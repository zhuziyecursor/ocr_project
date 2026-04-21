from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os
import uuid

from core.database import get_db
from core.config import settings
from schemas.document import DocumentResponse, DocumentListResponse, DocumentStatusResponse
from services.document_service import DocumentService
from services.compare_service import CompareService
from services.export_service import ExportService

router = APIRouter(prefix="/documents", tags=["documents"])


def validate_uuid(document_id: str) -> str:
    """Validate UUID format, raise 404 if invalid"""
    try:
        uuid.UUID(document_id)
        return document_id
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传文档接口"""
    service = DocumentService(db)
    return await service.upload_document(file)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取文档列表"""
    service = DocumentService(db)
    return await service.list_documents(skip=skip, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """获取单个文档详情"""
    document_id = validate_uuid(document_id)
    service = DocumentService(db)
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """获取文档处理状态"""
    document_id = validate_uuid(document_id)
    service = DocumentService(db)
    try:
        return await service.get_document_status(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """删除文档"""
    document_id = validate_uuid(document_id)
    service = DocumentService(db)
    success = await service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/result")
async def get_document_result(
    document_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """获取文档识别结果（result_json）"""
    document_id = validate_uuid(document_id)
    service = DocumentService(db)
    result = await service.get_document_result(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recognition result not found")
    return result


@router.get("/{document_id}/export")
async def export_document(
    document_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """导出文档识别结果为 Markdown"""
    document_id = validate_uuid(document_id)
    service = ExportService(db)
    try:
        content, filename = await service.export_markdown(document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """返回文档原始文件（用于前端 PDFViewer 渲染）"""
    import os
    import mimetypes
    document_id = validate_uuid(document_id)
    service = DocumentService(db)
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = document.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    def iter_file():
        with open(file_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    filename = os.path.basename(file_path)
    # URL-encode filename for Content-Disposition header compatibility
    from urllib.parse import quote
    encoded_filename = quote(filename, safe='')
    return StreamingResponse(
        iter_file(),
        media_type=mime_type,
        headers={"Content-Disposition": f"inline; filename*=utf-8''{encoded_filename}"}
    )


@router.post("/compare")
async def compare_documents(
    body: dict,
    db: AsyncSession = Depends(get_db)
):
    """跨文件比对，返回 diffs 列表"""
    doc_a_id = body.get("doc_a_id")
    doc_b_id = body.get("doc_b_id")
    if not doc_a_id or not doc_b_id:
        raise HTTPException(status_code=422, detail="doc_a_id and doc_b_id are required")
    try:
        uuid.UUID(doc_a_id)
        uuid.UUID(doc_b_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format")

    service = CompareService(db)
    try:
        diffs = await service.compare(doc_a_id, doc_b_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"diffs": diffs}

@router.get("/{document_id}/images/{image_name}")
async def get_document_image(
    document_id: str = Path(...),
    image_name: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """获取文档识别结果中的图片文件"""
    document_id = validate_uuid(document_id)

    # 安全检查：防止路径穿越
    if ".." in image_name or image_name.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid image name")

    # 从本地存储读取图片（从 api/documents.py 到项目根目录需要 3 层）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    local_path = os.path.join(project_root, "ocr_res", document_id, "images", image_name)

    from fastapi.responses import FileResponse
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(local_path)


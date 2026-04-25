import os
import uuid
import aiofiles
from fastapi import UploadFile
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document, RecognitionResult
from schemas.document import DocumentResponse, DocumentListResponse, DocumentStatusResponse
from core.config import settings
from tasks.document_tasks import process_document_task


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_document(self, file: UploadFile) -> DocumentResponse:
        """上传文档并根据大小决定同步/异步处理"""
        # 检查文件扩展名
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")

        # 读取文件内容
        content = await file.read()
        file_size = len(content)

        # 检查文件大小
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"文件大小超过限制: {settings.MAX_FILE_SIZE / 1024 / 1024}MB")

        # 生成文件路径
        file_id = str(uuid.uuid4())
        file_path = f"documents/{file_id}/{file.filename}"

        # 保存文件到本地存储
        save_dir = f"/app/source_file/{file_id}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{file.filename}"

        async with aiofiles.open(save_path, 'wb') as f:
            await f.write(content)

        # 创建文档记录
        document = Document(
            id=file_id,
            file_name=file.filename,
            file_path=save_path,
            file_size=file_size,
            status="PENDING",
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        # 判断同步/异步处理
        # 小文件（≤5MB且≤10页）同步处理，大文件异步
        # 简化判断：先用task，后续根据页数再优化
        task = process_document_task.delay(file_id, save_path)

        # 更新task_id
        document.task_id = task.id
        await self.db.commit()
        # 必须 refresh：第二次 commit 触发 server_default onupdate 更新 updated_at，
        # 但 Python 对象内存里没有新值，Pydantic model_validate 会触发 MissingGreenlet 异常
        await self.db.refresh(document)

        return DocumentResponse.model_validate(document)

    async def list_documents(self, skip: int = 0, limit: int = 100) -> DocumentListResponse:
        """获取文档列表"""
        result = await self.db.execute(
            select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
        )
        documents = result.scalars().all()

        count_result = await self.db.execute(select(Document))
        total = len(count_result.scalars().all())

        return DocumentListResponse(
            total=total,
            items=[DocumentResponse.model_validate(doc) for doc in documents]
        )

    async def get_document(self, document_id: str) -> DocumentResponse:
        """获取单个文档"""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document:
            return DocumentResponse.model_validate(document)
        return None

    async def get_document_status(self, document_id: str) -> DocumentStatusResponse:
        """获取文档处理状态"""
        document = await self.get_document(document_id)
        if not document:
            raise ValueError("Document not found")

        return DocumentStatusResponse(
            task_id=document.task_id or "",
            status=document.status,
            message=f"文档状态: {document.status}"
        )

    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        # 先删除关联的识别结果（按依赖顺序）
        await self.db.execute(
            delete(RecognitionResult).where(RecognitionResult.document_id == document_id)
        )
        await self.db.commit()

        # 再删除文档本身
        result = await self.db.execute(
            delete(Document).where(Document.id == document_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_document_result(self, document_id: str):
        """获取文档识别结果"""
        result = await self.db.execute(
            select(RecognitionResult).where(RecognitionResult.document_id == document_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return record.result_json

    async def update_document_status(self, document_id: str, status: str,
                                      error_message: str = None, total_pages: int = None):
        """更新文档状态"""
        update_data = {"status": status}
        if error_message:
            update_data["error_message"] = error_message
        if total_pages:
            update_data["total_pages"] = total_pages

        await self.db.execute(
            update(Document).where(Document.id == document_id).values(**update_data)
        )
        await self.db.commit()

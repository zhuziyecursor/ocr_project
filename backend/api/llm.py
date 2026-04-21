"""
LLM API - 调用豆包大模型进行 OCR 结果优化排版
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_service import llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


class OptimizeRequest(BaseModel):
    """优化请求"""
    ocr_text: str
    page_info: str = ""


class OptimizeResponse(BaseModel):
    """优化响应"""
    success: bool
    optimized_content: str
    error: str = ""


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_layout(request: OptimizeRequest):
    """
    调用大模型优化 OCR 内容的排版

    - **ocr_text**: OCR 识别的原始文本内容
    - **page_info**: 页码信息（如 "第 4 页"）
    """
    try:
        optimized_content = await llm_service.optimize_layout(
            request.ocr_text,
            request.page_info
        )
        return OptimizeResponse(
            success=True,
            optimized_content=optimized_content
        )
    except Exception as e:
        return OptimizeResponse(
            success=False,
            optimized_content="",
            error=str(e)
        )

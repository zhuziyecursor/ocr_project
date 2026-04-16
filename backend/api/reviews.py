from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from schemas.review import ReviewRecordCreate, ReviewRecordResponse
from services.review_service import ReviewService
from api.auth import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewRecordResponse)
async def create_review_record(
    record_data: ReviewRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建审核记录"""
    service = ReviewService(db)
    record = await service.create_review_record(record_data, current_user.username)
    return record


@router.get("/document/{document_id}", response_model=List[ReviewRecordResponse])
async def get_document_reviews(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取文档的所有审核记录"""
    service = ReviewService(db)
    return await service.get_document_reviews(document_id)


@router.put("/{record_id}", response_model=ReviewRecordResponse)
async def update_review_record(
    record_id: str,
    record_data: ReviewRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新审核记录"""
    service = ReviewService(db)
    record = await service.update_review_record(record_id, record_data, current_user.username)
    if not record:
        raise HTTPException(status_code=404, detail="Review record not found")
    return record

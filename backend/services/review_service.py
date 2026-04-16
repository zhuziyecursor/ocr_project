from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.review_record import ReviewRecord
from schemas.review import ReviewRecordCreate, ReviewRecordResponse


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_review_record(
        self, record_data: ReviewRecordCreate, reviewed_by: str
    ) -> ReviewRecordResponse:
        """创建审核记录"""
        record = ReviewRecord(
            document_id=record_data.document_id,
            block_id=record_data.block_id,
            page_no=record_data.page_no,
            original_content=record_data.original_content,
            modified_content=record_data.modified_content,
            reviewed_by=reviewed_by
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return ReviewRecordResponse.model_validate(record)

    async def get_document_reviews(self, document_id: str):
        """获取文档的所有审核记录"""
        result = await self.db.execute(
            select(ReviewRecord)
            .where(ReviewRecord.document_id == document_id)
            .order_by(ReviewRecord.reviewed_at.desc())
        )
        records = result.scalars().all()
        return [ReviewRecordResponse.model_validate(r) for r in records]

    async def update_review_record(
        self, record_id: str, record_data: ReviewRecordCreate, reviewed_by: str
    ):
        """更新审核记录"""
        result = await self.db.execute(
            select(ReviewRecord).where(ReviewRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        record.block_id = record_data.block_id
        record.page_no = record_data.page_no
        record.original_content = record_data.original_content
        record.modified_content = record_data.modified_content
        record.reviewed_by = reviewed_by

        await self.db.commit()
        await self.db.refresh(record)
        return ReviewRecordResponse.model_validate(record)

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReviewRecordCreate(BaseModel):
    document_id: str
    block_id: Optional[str] = None
    page_no: Optional[int] = None
    original_content: Optional[str] = None
    modified_content: Optional[str] = None
    reviewed_by: Optional[str] = None


class ReviewRecordResponse(BaseModel):
    id: str
    document_id: str
    block_id: Optional[str] = None
    page_no: Optional[int] = None
    original_content: Optional[str] = None
    modified_content: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: datetime

    class Config:
        from_attributes = True

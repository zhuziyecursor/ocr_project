from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DocumentCreate(BaseModel):
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    total_pages: Optional[int] = None
    uploaded_by: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    total_pages: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    uploaded_by: Optional[str] = None
    task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]


class DocumentStatusResponse(BaseModel):
    task_id: str
    status: str
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    message: Optional[str] = None
    document_id: Optional[str] = None

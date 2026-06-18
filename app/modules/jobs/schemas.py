from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime

class JobResponse(BaseModel):
    id: UUID4
    job_type: str
    status: str
    progress: int
    current_step: Optional[str]
    file_name: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    job_type: str
    file_name: Optional[str] = None

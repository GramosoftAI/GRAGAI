from pydantic import BaseModel, UUID4, computed_field
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

    @computed_field
    @property
    def time_taken(self) -> Optional[str]:
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            total_seconds = int(delta.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds}Sec"
            mins = total_seconds // 60
            secs = total_seconds % 60
            if secs == 0:
                return f"{mins}Mins"
            return f"{mins}Mins {secs}Sec"
        elif self.started_at and self.status in ["processing", "started"]:
            # If still running, show elapsed time
            from datetime import timezone
            now = datetime.now(timezone.utc) if self.started_at.tzinfo else datetime.utcnow()
            delta = now - self.started_at
            total_seconds = int(delta.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds}Sec"
            mins = total_seconds // 60
            secs = total_seconds % 60
            if secs == 0:
                return f"{mins}Mins"
            return f"{mins}Mins {secs}Sec"
        return None

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    job_type: str
    file_name: Optional[str] = None

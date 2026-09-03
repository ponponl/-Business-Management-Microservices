from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    attachment_id: UUID
    version_id: UUID

    file_name: str
    content_type: str | None = None
    file_size: int

    uploaded_by: UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class NotificationBase(BaseModel):
    title: str
    message: str
    event_type: str
    reference_id: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

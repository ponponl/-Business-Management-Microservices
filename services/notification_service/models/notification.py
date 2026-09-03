from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=True) # Dùng cho Idempotency
    user_id = Column(Integer, index=True, nullable=False) # ID của người nhận thông báo
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    event_type = Column(String, nullable=False) # VD: contract.approved, volume.recorded
    reference_id = Column(String, nullable=True) # VD: contract_number hoặc period_key
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

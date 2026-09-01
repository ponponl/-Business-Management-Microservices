from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from core.database import Base

# Bảng quản lý kì sản lượng
class OperationPeriod(Base):
    __tablename__ = "operation_periods"
    period_key = Column(String, primary_key=True, index=True) # e.g. "2026-08"
    status = Column(String, default="OPEN") # OPEN, LOCKED
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

# Bảng sản lượng thực tế
class OperationVolume(Base):
    __tablename__ = "operation_volumes"
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String, index=True)
    service_code = Column(String)
    volume_date = Column(DateTime)
    period_key = Column(String, ForeignKey("operation_periods.period_key"))
    quantity = Column(Float)
    unit = Column(String)
    recorded_by = Column(String)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# Bảng yêu cầu xin mở khóa kỳ
class UnlockPeriodRequest(Base):
    __tablename__ = "unlock_period_requests"
    id = Column(Integer, primary_key=True, index=True)
    period_key = Column(String, ForeignKey("operation_periods.period_key")) 
    requested_by = Column(String)
    reason = Column(String)
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    reject_reason = Column(String, nullable=True)
    target_type = Column(String, default="PERIOD")
    target_volume_id = Column(Integer, nullable=True)
    target_service_code = Column(String, nullable=True)
    old_quantity = Column(Float, nullable=True)
    proposed_quantity = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

# Bảng lịch sử thay đổi
class VolumeAuditLog(Base):
    __tablename__ = "volume_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    volume_id = Column(Integer)
    action = Column(String) # CREATE, UPDATE, DELETE
    old_data = Column(String, nullable=True) # JSON string
    new_data = Column(String, nullable=True) # JSON string
    actor_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

# Bảng Outbox Event để đảm bảo không mất event khi Kafka lỗi
class OperationOutboxEvent(Base):
    __tablename__ = "operation_outbox_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    payload = Column(String) # Lưu dạng JSON string
    status = Column(String, default="PENDING") # PENDING, PUBLISHED, FAILED
    created_at = Column(DateTime, server_default=func.now())


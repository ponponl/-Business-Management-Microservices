import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Date, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


# 1. Bảng SERVICE_ITEM (Dịch vụ)
class ServiceItem(Base):
    __tablename__ = "service_item"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_code = Column(String(50), unique=True, nullable=False)
    service_name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=True)
    status = Column(String(20), default="ACTIVE")

    # Quan hệ
    details = relationship("PriceListDetail", back_populates="service_item")
    usage_logs = relationship("PriceListUsageLog", back_populates="service_item")


# 2. Bảng PRICE_LIST (Bảng giá gốc)
class PriceList(Base):
    __tablename__ = "price_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_code = Column(String(50), unique=True, nullable=False)
    price_list_name = Column(String(255), nullable=False)

    # PRC-01: Phạm vi & Đối tượng áp dụng (CUSTOMER, CONTRACT, GENERAL, SERVICE_GROUP,...)
    scope_type = Column(String(50), nullable=False)
    scope_id = Column(String(50), nullable=True)

    description = Column(Text, nullable=True)

    # Audit Trail
    created_by = Column(UUID(as_uuid=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ
    versions = relationship("PriceListVersion", back_populates="price_list")
    details = relationship("PriceListDetail", back_populates="price_list")


# 3. Bảng PRICE_LIST_VERSION (Phiên bản bảng giá)
class PriceListVersion(Base):
    __tablename__ = "price_list_version"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_id = Column(UUID(as_uuid=True), ForeignKey("price_list.id"), nullable=False)
    version_number = Column(Integer, nullable=False)

    # PRC-02: Thời gian hiệu lực (valid_to = Null đại diện cho áp dụng vô thời hạn)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)

    # Đầy đủ 7 trạng thái: DRAFT, SUBMITTED, APPROVED, EFFECTIVE, REJECTED, SUPERSEDED, EXPIRED
    status = Column(String(30), default="DRAFT", nullable=False)

    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=True)
    workflow_instance_id = Column(UUID(as_uuid=True), nullable=True)

    # Luồng Phê duyệt 3 Role & Audit
    created_by = Column(UUID(as_uuid=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    approval_stage = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ
    price_list = relationship("PriceList", back_populates="versions")
    details = relationship("PriceListDetail", back_populates="price_list_version")
    change_histories = relationship("PriceChangeHistory", back_populates="price_list_version")
    usage_logs = relationship("PriceListUsageLog", back_populates="price_list_version")


# 4. Bảng PRICE_LIST_DETAIL (Chi tiết bảng giá)
class PriceListDetail(Base):
    __tablename__ = "price_list_detail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_id = Column(UUID(as_uuid=True), ForeignKey("price_list.id"), nullable=False)
    price_list_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=False)
    service_item_id = Column(UUID(as_uuid=True), ForeignKey("service_item.id"), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)

    # Quan hệ
    price_list = relationship("PriceList", back_populates="details")
    price_list_version = relationship("PriceListVersion", back_populates="details")
    service_item = relationship("ServiceItem", back_populates="details")


# 5. Bảng PRICE_CHANGE_HISTORY (Lịch sử thay đổi)
class PriceChangeHistory(Base):
    __tablename__ = "price_change_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_reason = Column(Text, nullable=True)
    changed_by = Column(UUID(as_uuid=True), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ
    price_list_version = relationship("PriceListVersion", back_populates="change_histories")


# 6. Bảng PRICE_LIST_USAGE_LOG (Nhật ký sử dụng bảng giá)
class PriceListUsageLog(Base):
    __tablename__ = "price_list_usage_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=False)
    billing_statement_id = Column(UUID(as_uuid=True), nullable=False)
    service_item_id = Column(UUID(as_uuid=True), ForeignKey("service_item.id"), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ
    price_list_version = relationship("PriceListVersion", back_populates="usage_logs")
    service_item = relationship("ServiceItem", back_populates="usage_logs")
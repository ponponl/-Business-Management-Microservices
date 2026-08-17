import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

# 1. Bảng SERVICE_ITEM (Dịch vụ)
class ServiceItem(Base):
    __tablename__ = "service_item"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Khóa chính của dịch vụ
    service_code = Column(String(50), unique=True, nullable=False)        # Mã dịch vụ duy nhất
    service_name = Column(String(255), nullable=False)                   # Tên dịch vụ
    unit = Column(String(50), nullable=True)                              # Đơn vị tính của dịch vụ
    status = Column(String(20), default="ACTIVE")                         # Trạng thái hoạt động của dịch vụ

    # Quan hệ
    details = relationship("PriceListDetail", back_populates="service_item")
    usage_logs = relationship("PriceListUsageLog", back_populates="service_item")


# 2. Bảng PRICE_LIST (Bảng giá gốc)
class PriceList(Base):
    __tablename__ = "price_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Khóa chính của bảng giá
    price_list_code = Column(String(50), unique=True, nullable=False)        # Mã định danh của bảng giá
    price_list_name = Column(String(255), nullable=False)                   # Tên bảng giá
    customer_id = Column(UUID(as_uuid=True), nullable=True)                 # Tham chiếu đến khách hàng áp dụng
    contract_id = Column(UUID(as_uuid=True), nullable=True)                 # Tham chiếu đến hợp đồng áp dụng
    scope_type = Column(String(50), nullable=False)                         # CUSTOMER, CONTRACT, SERVICE_GROUP, SERVICE_TYPE, GENERAL
    scope_id = Column(String(50), nullable=True)                            # Định danh của đối tượng áp dụng tương ứng với scope_type
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ
    versions = relationship("PriceListVersion", back_populates="price_list")
    details = relationship("PriceListDetail", back_populates="price_list")


# 3. Bảng PRICE_LIST_VERSION (Phiên bản bảng giá)
class PriceListVersion(Base):
    __tablename__ = "price_list_version"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)                       # Khóa chính của phiên bản
    price_list_id = Column(UUID(as_uuid=True), ForeignKey("price_list.id"), nullable=False)      # Khóa ngoại tham chiếu PRICE_LIST
    version_number = Column(Integer, nullable=False)                                           # Số phiên bản
    valid_from = Column(Date, nullable=False)                                                  # Ngày bắt đầu hiệu lực
    valid_to = Column(Date, nullable=False)                                                    # Ngày kết thúc hiệu lực
    status = Column(String(20), default="DRAFT")                                               # DRAFT, SUBMITTED, APPROVED, EFFECTIVE, SUPERSEDED, EXPIRED, REJECTED
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=True) # Tham chiếu phiên bản trước
    workflow_instance_id = Column(UUID(as_uuid=True), nullable=True)                           # Tham chiếu quy trình phê duyệt

    # Quan hệ
    price_list = relationship("PriceList", back_populates="versions")
    details = relationship("PriceListDetail", back_populates="price_list_version")
    change_histories = relationship("PriceChangeHistory", back_populates="price_list_version")
    usage_logs = relationship("PriceListUsageLog", back_populates="price_list_version")


# 4. Bảng PRICE_LIST_DETAIL (Chi tiết bảng giá)
class PriceListDetail(Base):
    __tablename__ = "price_list_detail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)                               # Khóa chính chi tiết bảng giá
    price_list_id = Column(UUID(as_uuid=True), ForeignKey("price_list.id"), nullable=False)              # Khóa ngoại tham chiếu PRICE_LIST
    price_list_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=False) # Khóa ngoại tham chiếu PRICE_LIST_VERSION
    service_item_id = Column(UUID(as_uuid=True), ForeignKey("service_item.id"), nullable=False)          # Khóa ngoại tham chiếu SERVICE_ITEM
    unit_price = Column(Numeric(15, 2), nullable=False)                                                 # Đơn giá dịch vụ

    # Quan hệ
    price_list = relationship("PriceList", back_populates="details")
    price_list_version = relationship("PriceListVersion", back_populates="details")
    service_item = relationship("ServiceItem", back_populates="details")


# 5. Bảng PRICE_CHANGE_HISTORY (Lịch sử thay đổi)
class PriceChangeHistory(Base):
    __tablename__ = "price_change_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)                               # Khóa chính bản ghi
    price_list_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=False) # Khóa ngoại tham chiếu PRICE_LIST_VERSION
    field_name = Column(String(100), nullable=False)                                                    # Tên trường dữ liệu thay đổi
    old_value = Column(Text, nullable=True)                                                             # Giá trị trước khi thay đổi
    new_value = Column(Text, nullable=True)                                                             # Giá trị sau khi thay đổi
    change_reason = Column(Text, nullable=True)                                                         # Lý do thực hiện thay đổi
    changed_by = Column(UUID(as_uuid=True), nullable=True)                                              # Người thực hiện thay đổi
    changed_at = Column(DateTime, default=datetime.utcnow)                                              # Thời điểm thực hiện thay đổi

    # Quan hệ
    price_list_version = relationship("PriceListVersion", back_populates="change_histories")


# 6. Bảng PRICE_LIST_USAGE_LOG (Nhật ký sử dụng bảng giá)
class PriceListUsageLog(Base):
    __tablename__ = "price_list_usage_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)                               # Khóa chính bản ghi sử dụng
    price_list_version_id = Column(UUID(as_uuid=True), ForeignKey("price_list_version.id"), nullable=False) # Khóa ngoại tham chiếu PRICE_LIST_VERSION
    billing_statement_id = Column(UUID(as_uuid=True), nullable=False)                                  # Tham chiếu đến Billing Service
    service_item_id = Column(UUID(as_uuid=True), ForeignKey("service_item.id"), nullable=False)          # Khóa ngoại tham chiếu SERVICE_ITEM
    applied_at = Column(DateTime, default=datetime.utcnow)                                              # Thời điểm sử dụng

    # Quan hệ
    price_list_version = relationship("PriceListVersion", back_populates="usage_logs")
    service_item = relationship("ServiceItem", back_populates="usage_logs")
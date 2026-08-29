from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


# --- Item Sidebar: Lịch sử phiên bản ---
class VersionHistoryItem(BaseModel):
    id: UUID
    version_number: str
    status: str
    valid_from: date
    valid_to: Optional[date] = None

    class Config:
        from_attributes = True


# --- Tab 1: Đơn giá chi tiết ---
class PriceDetailItem(BaseModel):
    service_item_id: UUID
    service_code: str
    service_name: str
    unit: Optional[str] = None
    unit_price: float

    class Config:
        from_attributes = True


class VersionDetailResponse(BaseModel):
    price_list_id: UUID
    price_list_code: str
    price_list_name: str
    scope_type: str
    scope_id: Optional[str] = None
    version_id: UUID
    version_number: str
    status: str
    valid_from: date
    valid_to: Optional[date] = None
    items: List[PriceDetailItem] = []

    class Config:
        from_attributes = True


# --- Tab 2: Nhật ký thay đổi ---
class ChangeHistoryItem(BaseModel):
    id: UUID
    entity_type: str
    entity_name: Optional[str] = None
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_reason: Optional[str] = None
    changed_by: Optional[UUID] = None
    changed_by_name: Optional[str] = None  # Đã JOIN với UserCache
    changed_at: datetime

    class Config:
        from_attributes = True


# --- Tab 3: Lịch sử áp dụng ---
class UsageLogItem(BaseModel):
    id: UUID
    payment_board_id: str
    service_item_id: Optional[UUID] = None
    service_code: Optional[str] = None
    service_name: Optional[str] = None
    applied_at: datetime

    class Config:
        from_attributes = True
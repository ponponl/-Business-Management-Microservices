from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# BASE (Class gốc dùng chung)

class VolumeBase(BaseModel):
    contract_id: str
    service_code: str
    volume_date: datetime
    period_key: str
    quantity: float
    unit: str



# INPUT (COMPARE / KIỂM TRA ĐẦU VÀO)
# Dùng để kiểm tra dữ liệu Frontend gửi lên

class VolumeCreate(VolumeBase):
    pass


class VolumeUpdate(BaseModel):
    quantity: float
    unit: Optional[str] = None
    service_code: Optional[str] = None

class PeriodLockRequest(BaseModel):
    pass 

class UnlockRequestCreate(BaseModel):
    reason: str
    target_type: Optional[str] = "PERIOD"
    target_volume_id: Optional[int] = None
    target_service_code: Optional[str] = None
    old_quantity: Optional[float] = None
    proposed_quantity: Optional[float] = None
    
class UnlockApprove(BaseModel):
    approved: bool
    reject_reason: Optional[str] = None


# OUTPUT (BỘ LỌC / RESPONSE)
# Dùng để lọc dữ liệu trước khi trả về Frontend/ SERVICE khác


class VolumeResponse(VolumeBase):
    id: int
    recorded_by: str
    is_locked: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class UnlockRequestResponse(BaseModel):
    id: int
    period_key: str
    requested_by: str
    reason: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    target_type: Optional[str] = "PERIOD"
    target_volume_id: Optional[int] = None
    target_service_code: Optional[str] = None
    old_quantity: Optional[float] = None
    proposed_quantity: Optional[float] = None
    reject_reason: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Trả qua Payment Service
class BillingSyncResponse(BaseModel):
    id: int
    contract_id: str
    service_code: str
    volume_date: datetime
    period_key: str
    quantity: float
    unit: str
    is_locked: bool
    period_status: str
    
    model_config = ConfigDict(from_attributes=True)
from pydantic import BaseModel
from typing import Optional, List


class ApprovalActionRequest(BaseModel):
    action: str  
    comment: Optional[str] = None  
    rejected_reason: Optional[str] = None 
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None


class ServiceDetailSchema(BaseModel):
    service_code: Optional[str] = None
    service_name: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = 0.0


class ApprovalResponse(BaseModel):
    price_list_id: str
    price_name: Optional[str] = None
    target_type: Optional[str] = None
    specific_target: Optional[str] = None
    version: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str
    approval_stage: str
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None
    message: str
    services: List[ServiceDetailSchema] = []

    class Config:
        from_attributes = True
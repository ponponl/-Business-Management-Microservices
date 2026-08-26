from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


class ApprovalActionRequest(BaseModel):
    action: str  # APPROVE, REJECT, SUBMIT
    comment: Optional[str] = None  
    rejected_reason: Optional[str] = Field(None, alias="rejectedReason") 
    approved_by: Optional[str] = Field(None, alias="approvedBy")
    rejected_by: Optional[str] = Field(None, alias="rejectedBy")

    class Config:
        populate_by_name = True


class ServiceDetailSchema(BaseModel):
    service_item_id: Optional[str] = Field(None, alias="serviceItemId")
    service_code: Optional[str] = Field(None, alias="serviceCode")
    service_name: Optional[str] = Field(None, alias="serviceName")
    service_group: Optional[str] = Field(None, alias="serviceGroup") 
    unit: Optional[str] = None
    price: Optional[Decimal] = Decimal("0.0") 

    class Config:
        from_attributes = True
        populate_by_name = True


class ApprovalResponse(BaseModel):
    price_list_id: str = Field(..., alias="priceListId")
    price_code: Optional[str] = Field(None, alias="priceCode") 
    price_name: Optional[str] = Field(None, alias="priceName")
    target_type: Optional[str] = Field(None, alias="targetType")
    specific_target: Optional[str] = Field(None, alias="specificTarget")
    version: Optional[str] = None
    effective_from: Optional[str] = Field(None, alias="effectiveFrom")
    effective_to: Optional[str] = Field(None, alias="effectiveTo")
    status: str
    approval_stage: Optional[str] = Field("MANAGER", alias="approvalStage")
    rejected_reason: Optional[str] = Field(None, alias="rejectedReason") 
    updated_by: Optional[str] = Field(None, alias="updatedBy")
    updated_at: Optional[str] = Field(None, alias="updatedAt")
    message: Optional[str] = "Success"
    services: List[ServiceDetailSchema] = []

    class Config:
        from_attributes = True
        populate_by_name = True
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ServiceItemResponse(BaseModel):
    id: UUID | str
    service_code: str = Field(..., alias="serviceCode")
    service_name: str = Field(..., alias="serviceName")
    service_group: Optional[str] = Field(None, alias="serviceGroup")
    unit: Optional[str] = "Lượt"
    status: str = "ACTIVE"

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PriceListStatsResponse(BaseModel):
    total: int
    submitted: int
    approved: int
    effective: int
    rejected: int
    superseded: int = 0
    expired: int = 0


class PriceListItemResponse(BaseModel):
    id: UUID | str
    price_code: Optional[str] = Field(None, alias="priceCode")
    name: str
    contractId: Optional[str] = None
    type: str
    version: str
    effectiveTime: str
    status: str
    updatedBy: Optional[str] = ""
    updatedAt: Optional[str] = ""
    rejectReason: Optional[str] = None
    rejectionReason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PriceListPaginatedResponse(BaseModel):
    items: List[PriceListItemResponse]
    total: int
    page: int
    page_size: int
    available_types: List[str]
    available_customers: List[str]


class PriceListItemCreate(BaseModel):
    service_item_id: Optional[UUID | str] = Field(None, alias="serviceItemId")
    service_code: str = Field(..., alias="serviceCode")
    service_name: str = Field(..., alias="serviceName")
    service_group: Optional[str] = Field(None, alias="serviceGroup")
    unit: str
    price: Decimal

    model_config = ConfigDict(populate_by_name=True)


class PriceListCreate(BaseModel):
    price_code: Optional[str] = Field(None, alias="priceCode")
    price_name: str = Field(..., alias="priceName")
    target_type: str = Field(..., alias="targetType")
    specific_target: Optional[str] = Field(None, alias="specificTarget")
    effective_from: date = Field(..., alias="effectiveFrom")
    effective_to: Optional[date] = Field(None, alias="effectiveTo")
    status: str = Field("DRAFT")
    version: str = "1.0"
    services: List[PriceListItemCreate]

    model_config = ConfigDict(populate_by_name=True)
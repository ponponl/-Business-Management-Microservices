from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field

class PriceListStatsResponse(BaseModel):
    total: int
    submitted: int
    approved: int
    effective: int
    rejected: int


class PriceListItemResponse(BaseModel):
    id: str
    name: str
    contractId: Optional[str] = None
    type: str
    version: str
    effectiveTime: str
    status: str
    updatedBy: str
    updatedAt: str


class PriceListPaginatedResponse(BaseModel):
    items: List[PriceListItemResponse]
    total: int
    page: int
    page_size: int
    available_types: List[str]
    available_customers: List[str]


class PriceListItemCreate(BaseModel):
    service_code: str = Field(..., alias="serviceCode")
    service_name: str = Field(..., alias="serviceName")
    unit: str
    price: float

    class Config:
        populate_by_name = True


class PriceListCreate(BaseModel):
    price_code: Optional[str] = Field(None, alias="priceCode")
    price_name: str = Field(..., alias="priceName")
    target_type: str = Field(..., alias="targetType")
    specific_target: Optional[str] = Field(None, alias="specificTarget")
    effective_from: date = Field(..., alias="effectiveFrom")
    effective_to: date = Field(..., alias="effectiveTo")
    status: str = Field("DRAFT")
    version: str = "1.0"
    services: List[PriceListItemCreate]

    class Config:
        populate_by_name = True
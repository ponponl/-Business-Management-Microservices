from pydantic import BaseModel
from typing import List, Optional


class PriceListStatsResponse(BaseModel):
    total: int
    submitted: int
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
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class ContractServiceItemResponse(BaseModel):
    service_item_id: UUID
    service_code: str
    service_name: str
    service_group: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Decimal

    class Config:
        from_attributes = True


class ContractServicesResponse(BaseModel):
    contract_id: str
    price_list_id: UUID
    price_list_code: str
    price_list_name: str
    version_id: UUID
    version_number: str
    services: List[ContractServiceItemResponse]
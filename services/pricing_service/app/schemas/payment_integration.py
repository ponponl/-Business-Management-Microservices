from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class PaymentValidationRequest(BaseModel):
    price_table_id: str = Field(..., description="ID hoặc Mã bảng giá (price_list_id hoặc price_list_code)")
    customer_id: Optional[str] = Field(None, description="ID khách hàng")
    contract_id: Optional[str] = Field(None, description="ID hợp đồng")
    period_start: date = Field(..., description="Ngày bắt đầu kỳ thanh toán")
    period_end: date = Field(..., description="Ngày kết thúc kỳ thanh toán")


class PriceItemDetail(BaseModel):
    service_item_id: str
    service_code: str
    service_name: str
    unit: Optional[str] = None
    unit_price: float


class PaymentValidationResponse(BaseModel):
    is_valid: bool
    price_list_id: str
    price_list_version_id: str
    version_number: str
    message: str
    items: List[PriceItemDetail] = []
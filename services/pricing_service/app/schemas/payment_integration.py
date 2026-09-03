from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class PaymentValidationRequest(BaseModel):
    price_table_id: str = Field(..., description="ID hoặc Mã bảng giá (price_list_id hoặc price_list_code)")
    customer_id: Optional[str] = Field(None, description="ID khách hàng")
    contract_id: Optional[str] = Field(None, description="ID hợp đồng")
    period_start: date = Field(..., description="Ngày bắt đầu kỳ thanh toán")
    period_end: date = Field(..., description="Ngày kết thúc kỳ thanh toán")


class PaymentPriceResolveRequest(BaseModel):
    customer_id: Optional[str] = None
    contract_id: Optional[str] = None
    operation_dates: List[date] = Field(default_factory=list)
    service_codes: List[str] = Field(default_factory=list)


class PriceItemDetail(BaseModel):
    service_item_id: str
    service_code: str
    service_name: str
    unit: Optional[str] = None
    unit_price: float
    operation_date: Optional[date] = None
    price_list_id: Optional[str] = None
    price_list_version_id: Optional[str] = None
    version_number: Optional[str] = None
    price_list_name: Optional[str] = None


class PaymentValidationResponse(BaseModel):
    is_valid: bool
    price_list_id: str
    price_list_version_id: str
    version_number: str
    message: str
    items: List[PriceItemDetail] = []
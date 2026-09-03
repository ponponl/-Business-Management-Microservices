from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PaymentDetailInput(BaseModel):
    service_code: str = Field(..., min_length=1, alias="serviceCode")
    service_name: str = Field(..., min_length=1, alias="serviceName")
    unit: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0, alias="unitPrice")

    class Config:
        populate_by_name = True


class PaymentBoardInput(BaseModel):
    code: str | None = None
    customer_id: str = Field(..., min_length=1, alias="customerId")
    contract_id: str = Field(..., min_length=1, alias="contractId")
    price_table_id: str = Field(..., min_length=1, alias="priceTableId")
    period_start: date = Field(..., alias="periodStart")
    period_end: date = Field(..., alias="periodEnd")
    tax_percent: Decimal = Field(Decimal("10"), ge=0, le=100, alias="taxPercent")
    reference_id: str | None = Field(None, alias="referenceId")
    period_id: str | None = Field(None, alias="periodId")
    items: list[PaymentDetailInput] = Field(..., min_length=1)

    class Config:
        populate_by_name = True

    @field_validator("period_end")
    @classmethod
    def valid_period(cls, value: date, info):
        if info.data.get("period_start") and value < info.data["period_start"]:
            raise ValueError("Kỳ kết thúc không được trước kỳ bắt đầu")
        return value


class ActionInput(BaseModel):
    comment: str | None = None


class CreateAdjustmentRequest(BaseModel):
    adjustment_reason: str = Field(..., min_length=1, alias="adjustmentReason")

    class Config:
        populate_by_name = True

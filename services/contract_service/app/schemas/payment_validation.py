from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PaymentContractValidationRequest(BaseModel):
    contract_id: UUID
    customer_id: UUID

    billing_period_start: date
    billing_period_end: date

    @model_validator(mode="after")
    def validate_billing_period(self):
        if self.billing_period_end < self.billing_period_start:
            raise ValueError(
                "Kỳ thanh toán kết thúc không được trước ngày bắt đầu"
            )

        return self


class PaymentContractValidationResponse(BaseModel):
    valid: bool

    contract_id: UUID | None = None
    contract_number: str | None = None
    customer_id: UUID | None = None

    status: str | None = None
    current_version: int | None = None

    effective_from: date | None = None
    effective_to: date | None = None

    reason_code: str | None = None
    message: str | None = None
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CreateContractRequest(BaseModel):
    customer_id: UUID

    effective_from: date
    effective_to: date

    contract_value: Decimal = Field(
        ge=0,
        max_digits=18,
        decimal_places=2,
    )

    payment_terms: str | None = None
    service_terms: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.effective_from > self.effective_to:
            raise ValueError(
                "effective_from must not be later than effective_to"
            )

        return self
    
class UpdateContractRequest(BaseModel):
    effective_from: date
    effective_to: date

    contract_value: Decimal = Field(
        ge=0,
        max_digits=18,
        decimal_places=2,
    )

    payment_terms: str | None = None
    service_terms: str | None = None

    row_version: int = Field(
        ge=1
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.effective_from > self.effective_to:
            raise ValueError(
                "effective_from must not be later than effective_to"
            )

        return self
    
class ContractVersionResponse(BaseModel):
    version_id: UUID
    contract_id: UUID
    version_no: int

    effective_from: date
    effective_to: date

    contract_value: Decimal

    payment_terms: str | None
    service_terms: str | None

    created_by: UUID
    created_at: str
    change_reason: str | None

    model_config = {
        "from_attributes": True
    }

class ContractResponse(BaseModel):
    contract_id: UUID
    customer_id: UUID

    current_version: int
    status: str
    row_version: int

    created_at: str
    updated_at: str

    current_version_detail: ContractVersionResponse | None = None

    model_config = {
        "from_attributes": True
    }
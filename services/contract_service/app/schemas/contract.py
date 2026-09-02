from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.attachment import AttachmentResponse


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
    created_at: datetime
    change_reason: str | None

    model_config = {
        "from_attributes": True
    }

class ContractResponse(BaseModel):
    contract_id: UUID
    contract_number: str
    customer_id: UUID

    current_version: int
    status: str
    row_version: int

    created_at: datetime
    updated_at: datetime

    current_version_detail: ContractVersionResponse | None = None
    
    attachments: list[AttachmentResponse] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }
    
class ContractListItem(BaseModel):
    contract_id: UUID
    contract_number: str
    customer_id: UUID
    
    current_version: int
    status: str
    row_version: int
    
    created_at: datetime
    updated_at: datetime
    
    effective_from: date | None = None
    effective_to: date | None = None
    contract_value: Decimal | None = None

    model_config = {
        "from_attributes": True
    }
    
class ContractListResponse(BaseModel):
    items: list[ContractListItem]
    
    total: int
    skip: int
    limit: int
    
class RenewContractRequest(BaseModel):
    new_effective_to: date
    reason: str
    
class CancelContractRequest(BaseModel):
    reason: str
    
class ApprovalActionRequest(BaseModel):
    comment: str | None = Field(
        default=None,
        max_length=2000,
    )
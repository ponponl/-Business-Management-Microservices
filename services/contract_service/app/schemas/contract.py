from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.contract_clock import contract_today
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

    payment_terms: str

    service_terms: str

    @field_validator("payment_terms", "service_terms")
    @classmethod
    def validate_required_terms(cls, value: str, info):
        if not value.strip():
            message = (
                "Vui lòng nhập điều khoản thanh toán."
                if info.field_name == "payment_terms"
                else "Vui lòng nhập điều khoản dịch vụ."
            )
            raise ValueError(message)
        return value.strip()

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.effective_from < contract_today():
            raise ValueError(
                "Ngày bắt đầu hiệu lực phải từ hôm nay trở đi."
            )

        if self.effective_from >= self.effective_to:
            raise ValueError(
                "Ngày bắt đầu hiệu lực phải trước ngày kết thúc hiệu lực."
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

    payment_terms: str

    service_terms: str

    @field_validator("payment_terms", "service_terms")
    @classmethod
    def validate_required_terms(cls, value: str, info):
        if not value.strip():
            message = (
                "Vui lòng nhập điều khoản thanh toán."
                if info.field_name == "payment_terms"
                else "Vui lòng nhập điều khoản dịch vụ."
            )
            raise ValueError(message)
        return value.strip()

    row_version: int = Field(
        ge=1
    )

    removed_attachment_ids: list[UUID] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.effective_from < contract_today():
            raise ValueError(
                "Ngày bắt đầu hiệu lực phải từ hôm nay trở đi."
            )

        if self.effective_from >= self.effective_to:
            raise ValueError(
                "Ngày bắt đầu hiệu lực phải trước ngày kết thúc hiệu lực."
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
    approvals: list["ContractApprovalResponse"] = Field(default_factory=list)
    current_approval_round: int | None = None
    director_approval_status: str | None = None
    revision_round: int | None = None
    revision_source: str | None = None
    manager_revision_reason: str | None = None
    director_revision_reason: str | None = None
    manager_send_revision_reason: str | None = None
    revision_reason_for_staff: str | None = None
    revision_reason_source_for_staff: str | None = None
    revision_reason_for_manager: str | None = None
    revision_reason_source_for_manager: str | None = None
    revision_reason_for_director: str | None = None
    revision_reason_source_for_director: str | None = None

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
    current_approval_round: int | None = None
    director_approval_status: str | None = None
    revision_round: int | None = None
    revision_source: str | None = None
    manager_revision_reason: str | None = None
    director_revision_reason: str | None = None
    manager_send_revision_reason: str | None = None
    revision_reason_for_staff: str | None = None
    revision_reason_source_for_staff: str | None = None
    revision_reason_for_manager: str | None = None
    revision_reason_source_for_manager: str | None = None
    revision_reason_for_director: str | None = None
    revision_reason_source_for_director: str | None = None

    model_config = {
        "from_attributes": True
    }
    
class ContractSummary(BaseModel):
    total: int = 0
    draft: int = 0
    submitted: int = 0
    manager_review: int = 0
    director_review: int = 0
    approved: int = 0
    active: int = 0
    revision_requested: int = 0
    revision_requested_by_manager: int = 0
    revision_requested_by_director: int = 0
    rejected: int = 0
    expired: int = 0
    cancelled: int = 0

class ContractApprovalResponse(BaseModel):
    approval_id: UUID
    approval_round: int
    step_no: int
    approver_id: UUID
    status: str
    comment: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ContractListResponse(BaseModel):
    items: list[ContractListItem]
    
    total: int
    skip: int
    limit: int
    summary: ContractSummary

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

class SendRevisionRequest(BaseModel):
    comment: str = Field(..., min_length=1)

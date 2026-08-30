from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ContractEventPayload(BaseModel):
    contract_id: UUID
    contract_number: str
    customer_id: UUID

    current_version: int
    status: str

    effective_from: date | None = None
    effective_to: date | None = None

class ContractEvent(BaseModel):
    event_id: UUID
    event_name: str
    occurred_at: datetime

    aggregate_type: str = "CONTRACT"
    aggregate_id: UUID

    version: int = 1

    payload: dict
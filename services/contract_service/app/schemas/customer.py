from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CustomerResponse(BaseModel):
    customer_id: UUID
    customer_code: str
    tax_code: str
    company_name: str
    representative_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

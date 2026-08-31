from pydantic import BaseModel, ConfigDict
from datetime import datetime

# class CustomerCacheSchema(BaseModel):
#     id: int
#     code: str
#     name: str
#     status: str
#     model_config = ConfigDict(from_attributes=True)

class ContractCacheSchema(BaseModel):
    id: int
    contract_number: str
    customer_id: int
    start_date: datetime
    end_date: datetime
    status: str
    model_config = ConfigDict(from_attributes=True)

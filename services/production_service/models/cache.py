from sqlalchemy import Column, Integer, String, DateTime
from core.database import Base

# class CustomerCache(Base):
#     __tablename__ = "customers_cache"
#     id = Column(Integer, primary_key=True, index=True)
#     code = Column(String, unique=True, index=True)
#     name = Column(String)
#     status = Column(String)

class ContractCache(Base):
    __tablename__ = "contracts_cache"
    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String, unique=True, index=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String)

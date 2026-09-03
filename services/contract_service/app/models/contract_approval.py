import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class ContractApproval(Base):
    __tablename__ = "contract_approvals"

    approval_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    contract_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
    )
    
    approval_round = Column(
        Integer,
        nullable=False,
        default=1,
        index=True,
    )

    step_no = Column(
        Integer,
        nullable=False,
    )

    approver_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True,
    )

    comment = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contract = relationship(
        "Contract",
        backref="approval_records",
    )
import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint

from app.db.session import Base


class ContractVersion(Base):
    __tablename__ = "contract_versions"
    
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "version_no",
            name="uq_contract_version",
        ),
        CheckConstraint(
            "effective_from <= effective_to",
            name="ck_contract_version_dates",
        ),
    )

    version_id = Column(
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

    version_no = Column(
        Integer,
        nullable=False,
    )

    effective_from = Column(
        Date,
        nullable=False,
    )

    effective_to = Column(
        Date,
        nullable=False,
    )

    contract_value = Column(
        Numeric(18, 2),
        nullable=False,
    )

    payment_terms = Column(
        Text,
        nullable=True,
    )

    service_terms = Column(
        Text,
        nullable=True,
    )

    created_by = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    change_reason = Column(
        Text,
        nullable=True,
    )

    contract = relationship(
        "Contract",
        back_populates="versions",
    )
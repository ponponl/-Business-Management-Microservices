import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class ContractAudit(Base):
    __tablename__ = "contract_audits"

    audit_id = Column(
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

    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contract_versions.version_id"),
        nullable=True,
        index=True,
    )

    actor_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    action = Column(
        String(50),
        nullable=False,
    )

    status_before = Column(
        String(30),
        nullable=True,
    )

    status_after = Column(
        String(30),
        nullable=True,
    )

    note = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    contract = relationship(
        "Contract",
        back_populates="audits",
    )
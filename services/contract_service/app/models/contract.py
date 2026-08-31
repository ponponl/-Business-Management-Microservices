import uuid

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Contract(Base):
    __tablename__ = "contracts"

    contract_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    contract_number = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.customer_id"),
        nullable=False,
        index=True,
    )

    current_version = Column(
        Integer,
        nullable=False,
        default=1,
    )

    status = Column(
        String(30),
        nullable=False,
        default="DRAFT",
        index=True,
    )

    row_version = Column(
        Integer,
        nullable=False,
        default=1,
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

    customer = relationship(
        "Customer",
        backref="contracts",
    )

    versions = relationship(
        "ContractVersion",
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    audits = relationship(
        "ContractAudit",
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    @property
    def effective_from(self):
        for version in self.versions:
            if version.version_no == self.current_version:
                return version.effective_from
        return None

    @property
    def effective_to(self):
        for version in self.versions:
            if version.version_no == self.current_version:
                return version.effective_to
        return None

    @property
    def contract_value(self):
        for version in self.versions:
            if version.version_no == self.current_version:
                return version.contract_value
        return None
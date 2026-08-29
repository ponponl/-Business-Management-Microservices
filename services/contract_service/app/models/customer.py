import uuid

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    customer_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    tax_code = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    company_name = Column(
        String(255),
        nullable=False,
    )

    representative_name = Column(
        String(255),
        nullable=True,
    )

    email = Column(
        String(255),
        nullable=True,
    )

    phone = Column(
        String(50),
        nullable=True,
    )

    address = Column(
        String,
        nullable=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="ACTIVE",
        index=True,
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
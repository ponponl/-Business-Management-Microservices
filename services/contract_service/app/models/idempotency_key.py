from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.session import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    key = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    operation = Column(
        String(50),
        nullable=False,
    )

    resource_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    request_hash = Column(
        String(64),
        nullable=False,
    )

    response_status = Column(
        Integer,
        nullable=False,
    )

    response_body = Column(
        JSONB,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.session import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    event_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    aggregate_type = Column(
        String(50),
        nullable=False,
    )

    aggregate_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    event_type = Column(
        String(100),
        nullable=False,
        index=True,
    )

    payload = Column(
        JSONB,
        nullable=False,
    )

    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )

    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    occurred_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    last_error = Column(
        Text,
        nullable=True,
    )
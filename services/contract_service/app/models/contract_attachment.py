import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class ContractAttachment(Base):
    __tablename__ = "contract_attachments"

    attachment_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contract_versions.version_id"),
        nullable=False,
        index=True,
    )

    file_name = Column(
        String(255),
        nullable=False,
    )

    object_key = Column(
        Text,
        nullable=False,
    )

    content_type = Column(
        String(100),
        nullable=False,
    )

    file_size = Column(
        BigInteger,
        nullable=False,
    )

    uploaded_by = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    version = relationship(
        "ContractVersion",
        backref="attachments",
    )
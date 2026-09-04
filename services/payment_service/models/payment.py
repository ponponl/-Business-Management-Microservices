import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from models.database import Base


class PaymentBoard(Base):
    __tablename__ = "payment_boards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), nullable=False)
    contract_id = Column(String(36), nullable=False)
    price_table_id = Column(String(36), nullable=False)
    price_list_id = Column(String(36), nullable=True)
    price_list_version_id = Column(String(36), nullable=True, index=True)
    price_list_version_number = Column(String(50), nullable=True)
    price_list_usages = Column(Text, nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    sub_total = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    tax_percent = Column(Numeric(5, 2), default=Decimal("10.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    status = Column(String(30), default="DRAFT", nullable=False)
    payment_type = Column(String(30), default="STANDARD", nullable=False)
    parent_payment_id = Column(String(36), ForeignKey("payment_boards.id", ondelete="SET NULL"), nullable=True, index=True)
    adjustment_reason = Column(Text, nullable=True)
    reference_id = Column(String(36), nullable=True)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    items = relationship("PaymentDetail", back_populates="statement", cascade="all, delete-orphan")
    signatures = relationship("PaymentSignature", back_populates="statement", cascade="all, delete-orphan")
    parent_payment = relationship("PaymentBoard", remote_side=[id], back_populates="adjustments")
    adjustments = relationship("PaymentBoard", back_populates="parent_payment", passive_deletes=True)

    __table_args__ = (
        Index("ix_payment_boards_parent_status", "parent_payment_id", "status"),
    )


class PaymentSignature(Base):
    __tablename__ = "payment_signatures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_board_id = Column(String(36), ForeignKey("payment_boards.id"), nullable=False, index=True)
    assignee_id = Column(String(36), nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    statement = relationship("PaymentBoard", back_populates="signatures")


class PaymentDetail(Base):
    __tablename__ = "payment_details"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_board_id = Column(String(36), ForeignKey("payment_boards.id"), nullable=False)
    operation_date = Column(Date, nullable=True)
    service_code = Column(String(50), nullable=False)
    service_name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    quantity = Column(Numeric(15, 2), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    total_price = Column(Numeric(15, 2), nullable=False)
    price_list_name = Column(String(255), nullable=True)
    price_list_code = Column(String(100), nullable=True)
    price_list_version_id = Column(String(36), nullable=True)
    price_list_version_number = Column(String(50), nullable=True)
    statement = relationship("PaymentBoard", back_populates="items")


class PaymentOutboxEvent(Base):
    __tablename__ = "payment_outbox_event"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    payload = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PaymentIdempotencyKey(Base):
    __tablename__ = "payment_idempotency_key"

    key = Column(String(100), primary_key=True)
    statement_id = Column(String(36), ForeignKey("payment_boards.id"), nullable=False)
    request_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PaymentWorkflow(Base):
    __tablename__ = "payment_workflow_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_board_id = Column(String(36), ForeignKey("payment_boards.id"), unique=True, nullable=False)
    current_step = Column(Integer, default=1, nullable=False)
    status = Column(String(30), default="IN_PROGRESS", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    steps = relationship("PaymentWorkflowStep", back_populates="workflow", cascade="all, delete-orphan")


class PaymentWorkflowStep(Base):
    __tablename__ = "payment_workflow_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("payment_workflow_instances.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    assignee_id = Column(String(36), nullable=False)
    status = Column(String(30), default="PENDING", nullable=False)
    action = Column(String(30), nullable=True)
    comment = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    workflow = relationship("PaymentWorkflow", back_populates="steps")

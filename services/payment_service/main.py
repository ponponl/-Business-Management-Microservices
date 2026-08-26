from datetime import date, datetime
from decimal import Decimal
import json
import os
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text, create_engine, func, select
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@postgres-payment:5432/db_payment")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PaymentBoard(Base):
    __tablename__ = "payment_boards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_code = Column(String(50), unique=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
    contract_code = Column(String(100), nullable=False)
    price_list_code = Column(String(100), nullable=False)
    period_from = Column(Date, nullable=False)
    period_to = Column(Date, nullable=False)
    status = Column(String(30), default="DRAFT", nullable=False)
    tax_rate = Column(Numeric(5, 2), default=Decimal("10.00"), nullable=False)
    note = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sign_status = Column(String(30), default="NOT_STARTED", nullable=False)
    sign_session_id = Column(String(100), nullable=True)
    items = relationship("PaymentDetail", back_populates="statement", cascade="all, delete-orphan")


class PaymentDetail(Base):
    __tablename__ = "payment_details"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id = Column(String(36), ForeignKey("payment_boards.id"), nullable=False)
    service_code = Column(String(50), nullable=False)
    service_name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    quantity = Column(Numeric(15, 2), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    statement = relationship("PaymentBoard", back_populates="items")


class PaymentAuditLog(Base):
    __tablename__ = "payment_status_histories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id = Column(String(36), ForeignKey("payment_boards.id"), nullable=False)
    actor = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def initialize_database():
    for attempt in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)


initialize_database()



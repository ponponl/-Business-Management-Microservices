import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.database import Base, SessionLocal, engine, get_db, initialize_database
from models.payment import (
    PaymentAuditLog,
    PaymentBoard,
    PaymentDetail,
    PaymentIdempotencyKey,
    PaymentOutboxEvent,
    PaymentWorkflow,
    PaymentWorkflowStep,
)
from schemas.payment import ActionInput, PaymentBoardInput
from services.outbox import OutboxPublisher
from services.source_validation import validate_payment_sources
from services.workflow import create_workflow, current_step
from utils.calculations import calculate_totals


initialize_database()
outbox_publisher = OutboxPublisher()


def add_audit(db: Session, statement: PaymentBoard, actor_id: str, action: str, from_status: str | None, note: str | None):
    db.add(PaymentAuditLog(
        payment_board_id=statement.id,
        action=action,
        from_status=from_status,
        status=statement.status,
        actor_id=actor_id,
        note=note,
    ))


def add_event(db: Session, event_type: str, statement: PaymentBoard):
    db.add(PaymentOutboxEvent(
        event_type=event_type,
        aggregate_id=statement.id,
        payload=json.dumps(serialize(statement), default=str),
    ))


def serialize(statement: PaymentBoard):
    subtotal, tax, total = calculate_totals(statement)
    return {
        "id": statement.id,
        "code": statement.code,
        "customerId": statement.customer_id,
        "contractId": statement.contract_id,
        "priceTableId": statement.price_table_id,
        "periodStart": statement.period_start.isoformat(),
        "periodEnd": statement.period_end.isoformat(),
        "status": statement.status,
        "taxPercent": float(statement.tax_percent),
        "subTotal": float(subtotal),
        "taxAmount": float(tax),
        "totalAmount": float(total),
        "referenceId": statement.reference_id,
        "createdBy": statement.created_by,
        "createdAt": statement.created_at.isoformat() if statement.created_at else None,
        "items": [{
            "id": item.id,
            "serviceCode": item.service_code,
            "serviceName": item.service_name,
            "unit": item.unit,
            "quantity": float(item.quantity),
            "unitPrice": float(item.unit_price),
            "totalPrice": float(item.total_price),
        } for item in statement.items],
    }


def make_items(items):
    return [PaymentDetail(
        service_code=item["service_code"],
        service_name=item["service_name"],
        unit=item["unit"],
        quantity=item["quantity"],
        unit_price=item["unit_price"],
        total_price=item["quantity"] * item["unit_price"],
    ) for item in items]


def create_board(payload: PaymentBoardInput, items, code: str, created_by: str, reference_id: str | None = None):
    statement = PaymentBoard(
        code=code,
        customer_id=payload.customer_id,
        contract_id=payload.contract_id,
        price_table_id=payload.price_table_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        tax_percent=payload.tax_percent,
        reference_id=reference_id or payload.reference_id,
        created_by=created_by,
        status="CALCULATED",
    )
    statement.items = make_items(items)
    statement.sub_total, statement.tax_amount, statement.total_amount = calculate_totals(statement)
    return statement


async def lifespan(app: FastAPI):
    task = asyncio.create_task(outbox_publisher.run())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await outbox_publisher.stop()


app = FastAPI(title="Payment Service API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"service": "Payment Service", "status": "active", "database": "Connected & Tables Synced"}


@app.get("/api/payments/stats")
def payment_stats(db: Session = Depends(get_db)):
    rows = db.execute(select(PaymentBoard.status, func.count(PaymentBoard.id)).group_by(PaymentBoard.status)).all()
    values = {name.lower(): count for name, count in rows}
    return {"total": sum(values.values()), "draft": values.get("draft", 0), "submitted": values.get("submitted", 0), "approved": values.get("approved", 0), "signed": values.get("signed", 0), "issued": values.get("issued", 0)}


@app.get("/api/payments")
def list_payments(status_filter: str | None = Query(None, alias="status"), search: str | None = None, db: Session = Depends(get_db)):
    query = select(PaymentBoard).order_by(PaymentBoard.created_at.desc())
    if status_filter and status_filter != "Tất cả":
        query = query.where(PaymentBoard.status == status_filter.upper())
    if search:
        query = query.where(PaymentBoard.code.ilike(f"%{search.strip()}%"))
    items = db.scalars(query).all()
    return {"items": [serialize(item) for item in items], "total": len(items)}


@app.post("/api/payments", status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentBoardInput, request: Request, db: Session = Depends(get_db)):
    key = request.headers.get("Idempotency-Key")
    if key:
        existing_key = db.get(PaymentIdempotencyKey, key)
        if existing_key:
            return serialize(db.get(PaymentBoard, existing_key.statement_id))
    code = payload.code or f"PAY-{datetime.utcnow():%Y%m%d%H%M%S}"
    if db.scalar(select(PaymentBoard).where(PaymentBoard.code == code)):
        raise HTTPException(409, "Mã bảng thanh toán đã tồn tại")
    items = validate_payment_sources(payload, request.headers.get("Authorization"))
    statement = create_board(payload, items, code, request.headers.get("X-User", "STAFF"))
    db.add(statement)
    db.flush()
    add_audit(db, statement, request.headers.get("X-User", "STAFF"), "CREATE", None, None)
    if key:
        db.add(PaymentIdempotencyKey(key=key, statement_id=statement.id))
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.get("/api/payments/{payment_id}")
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    return serialize(statement)


@app.put("/api/payments/{payment_id}")
def update_payment(payment_id: str, payload: PaymentBoardInput, request: Request, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.status not in {"DRAFT", "CALCULATED", "RECONCILED", "REVISION_REQUESTED"}:
        raise HTTPException(409, "Bảng thanh toán đã khóa, cần tạo hồ sơ điều chỉnh")
    items = validate_payment_sources(payload, request.headers.get("Authorization"))
    previous_status = statement.status
    statement.customer_id = payload.customer_id
    statement.contract_id = payload.contract_id
    statement.price_table_id = payload.price_table_id
    statement.period_start = payload.period_start
    statement.period_end = payload.period_end
    statement.tax_percent = payload.tax_percent
    statement.reference_id = payload.reference_id
    statement.items = make_items(items)
    statement.status = "CALCULATED"
    statement.sub_total, statement.tax_amount, statement.total_amount = calculate_totals(statement)
    add_audit(db, statement, request.headers.get("X-User", "STAFF"), "UPDATE", previous_status, None)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


def change_status(payment_id: str, next_status: str, payload: ActionInput, db: Session, actor: str, assignees: list[str] | None = None):
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    allowed = {"RECONCILED": {"CALCULATED", "REVISION_REQUESTED"}, "SUBMITTED": {"RECONCILED"}, "APPROVED": {"SUBMITTED"}, "REJECTED": {"SUBMITTED"}, "REVISION_REQUESTED": {"SUBMITTED"}}
    if statement.status not in allowed[next_status]:
        raise HTTPException(409, f"Không thể chuyển từ {statement.status} sang {next_status}")
    subtotal, tax, total = calculate_totals(statement)
    statement.sub_total, statement.tax_amount, statement.total_amount = subtotal, tax, total
    if next_status == "SUBMITTED" and (total < 0 or not statement.items):
        raise HTTPException(422, "Bảng thanh toán phải có dòng dịch vụ và tổng tiền không âm")
    if next_status in {"REJECTED", "REVISION_REQUESTED"} and not payload.comment:
        raise HTTPException(422, "Bắt buộc nhập lý do khi từ chối hoặc yêu cầu chỉnh sửa")
    previous_status = statement.status
    final_status = next_status
    if next_status in {"APPROVED", "REJECTED", "REVISION_REQUESTED"}:
        workflow, step = current_step(db, statement)
        if step.assignee_id != actor:
            raise HTTPException(403, "Bạn không được giao xử lý bước phê duyệt hiện tại")
        step.action = next_status
        step.comment = payload.comment
        step.completed_at = datetime.utcnow()
        if next_status == "APPROVED" and step.step_no < len(workflow.steps):
            step.status = "COMPLETED"
            workflow.current_step = step.step_no + 1
            final_status = "SUBMITTED"
        else:
            step.status = "COMPLETED" if next_status == "APPROVED" else "REJECTED"
            workflow.status = "COMPLETED"
    statement.status = final_status
    add_audit(db, statement, actor, next_status, previous_status, payload.comment)
    add_event(db, f"payment.{next_status.lower()}", statement)
    if next_status == "SUBMITTED":
        create_workflow(db, statement, assignees or [])
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.post("/api/payments/{payment_id}/reconcile")
def reconcile(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    return change_status(payment_id, "RECONCILED", payload, db, request.headers.get("X-User", "STAFF"))


@app.post("/api/payments/{payment_id}/submit")
def submit(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    assignees = [value.strip() for value in request.headers.get("X-Approval-Assignees", "").split(",") if value.strip()]
    return change_status(payment_id, "SUBMITTED", payload, db, request.headers.get("X-User", "STAFF"), assignees)


@app.post("/api/payments/{payment_id}/approve")
def approve(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    return change_status(payment_id, "APPROVED", payload, db, request.headers.get("X-User", "MANAGER"))


@app.post("/api/payments/{payment_id}/reject")
def reject(payment_id: str, payload: ActionInput, request: Request, db: Session = Depends(get_db)):
    return change_status(payment_id, "REJECTED", payload, db, request.headers.get("X-User", "MANAGER"))


@app.post("/api/payments/{payment_id}/request-revision")
def request_revision(payment_id: str, payload: ActionInput, request: Request, db: Session = Depends(get_db)):
    return change_status(payment_id, "REVISION_REQUESTED", payload, db, request.headers.get("X-User", "MANAGER"))


@app.post("/api/payments/{payment_id}/send-sign")
def send_sign(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement or statement.status not in {"APPROVED", "SIGN_FAILED", "SIGN_CANCELLED"}:
        raise HTTPException(409, "Chỉ bảng thanh toán đã duyệt mới được gửi ký")
    previous_status = statement.status
    statement.status = "SIGNING"
    add_audit(db, statement, request.headers.get("X-User", "STAFF"), "SEND_SIGN", previous_status, None)
    add_event(db, "payment.sign_requested", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.post("/api/payments/{payment_id}/sign-callback")
def sign_callback(payment_id: str, success: bool = True, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement or statement.status != "SIGNING":
        raise HTTPException(409, "Phiên ký không hợp lệ")
    previous_status = statement.status
    statement.status = "SIGNED" if success else "SIGN_FAILED"
    add_audit(db, statement, "E_SIGN_SERVICE", "SIGN_CALLBACK", previous_status, None)
    add_event(db, "payment.signed" if success else "payment.sign_failed", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.post("/api/payments/{payment_id}/issue")
def issue_payment(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.status != "SIGNED":
        raise HTTPException(409, "Chỉ bảng thanh toán đã ký mới được phát hành")
    previous_status = statement.status
    statement.status = "ISSUED"
    add_audit(db, statement, request.headers.get("X-User", "STAFF"), "ISSUE", previous_status, None)
    add_event(db, "payment.issued", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.post("/api/payments/{payment_id}/cancel-sign")
def cancel_sign(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement or statement.status != "SIGNING":
        raise HTTPException(409, "Chỉ phiên ký đang xử lý mới được hủy")
    previous_status = statement.status
    statement.status = "SIGN_CANCELLED"
    add_audit(db, statement, request.headers.get("X-User", "STAFF"), "CANCEL_SIGN", previous_status, None)
    add_event(db, "payment.sign_cancelled", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.get("/api/payments/{payment_id}/workflow")
def get_workflow(payment_id: str, db: Session = Depends(get_db)):
    workflow = db.scalar(select(PaymentWorkflow).where(PaymentWorkflow.payment_board_id == payment_id))
    if not workflow:
        raise HTTPException(404, "Hồ sơ chưa có workflow")
    return {"id": workflow.id, "paymentBoardId": workflow.payment_board_id, "status": workflow.status, "currentStep": workflow.current_step, "steps": [{
        "stepNo": step.step_no, "assigneeId": step.assignee_id, "status": step.status,
        "action": step.action, "comment": step.comment,
        "completedAt": step.completed_at.isoformat() if step.completed_at else None,
    } for step in sorted(workflow.steps, key=lambda item: item.step_no)]}


@app.post("/api/payments/{payment_id}/adjustment", status_code=status.HTTP_201_CREATED)
def create_adjustment(payment_id: str, payload: PaymentBoardInput, request: Request, db: Session = Depends(get_db)):
    original = db.get(PaymentBoard, payment_id)
    if not original:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán gốc")
    if original.status not in {"APPROVED", "SIGNED", "ISSUED"}:
        raise HTTPException(409, "Chỉ hồ sơ đã duyệt hoặc đã ký mới được tạo điều chỉnh")
    code = payload.code or f"ADJ-{datetime.utcnow():%Y%m%d%H%M%S}"
    if db.scalar(select(PaymentBoard).where(PaymentBoard.code == code)):
        raise HTTPException(409, "Mã bảng điều chỉnh đã tồn tại")
    items = validate_payment_sources(payload, request.headers.get("Authorization"))
    statement = create_board(payload, items, code, request.headers.get("X-User", "STAFF"), original.id)
    db.add(statement)
    db.flush()
    add_audit(db, statement, request.headers.get("X-User", "STAFF"), "CREATE_ADJUSTMENT", None, f"reference_id={original.id}")
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@app.get("/api/payments/{payment_id}/history")
def payment_history(payment_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(PaymentAuditLog).where(PaymentAuditLog.payment_board_id == payment_id).order_by(PaymentAuditLog.created_at)).all()
    return [{"id": row.id, "action": row.action, "fromStatus": row.from_status, "status": row.status, "actorId": row.actor_id, "note": row.note, "createdAt": row.created_at.isoformat()} for row in rows]


@app.get("/api/payments/outbox/pending")
def pending_outbox(db: Session = Depends(get_db)):
    rows = db.scalars(select(PaymentOutboxEvent).where(PaymentOutboxEvent.published_at.is_(None)).order_by(PaymentOutboxEvent.created_at)).all()
    return {"count": len(rows), "items": [{"id": row.id, "eventType": row.event_type, "aggregateId": row.aggregate_id, "createdAt": row.created_at.isoformat()} for row in rows]}

import json
import calendar
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.database import get_db
from models.payment import (
    PaymentBoard,
    PaymentDetail,
    PaymentIdempotencyKey,
    PaymentOutboxEvent,
    PaymentSignature,
    PaymentWorkflow,
    PaymentWorkflowStep,
)
from schemas.payment import ActionInput, PaymentBoardInput
from services.source_validation import validate_payment_sources
from services.workflow import create_workflow, current_step
from utils.calculations import calculate_totals
from utils.http_client import call_json

PRODUCTION_SERVICE_URL = "http://production-service:8000"

router = APIRouter(prefix="/api/v1", tags=["payments"])


def add_event(db: Session, event_type: str, statement: PaymentBoard):
    db.add(PaymentOutboxEvent(
        event_type=event_type,
        aggregate_id=statement.id,
        payload=json.dumps(serialize(statement), default=str),
    ))


def add_signing_event(db: Session, signature: PaymentSignature):
    db.add(PaymentOutboxEvent(
        event_type="payment.signing",
        aggregate_id=signature.payment_board_id,
        payload=json.dumps({
            "signature_id": signature.id,
            "payment_board_id": signature.payment_board_id,
            "assignee_id": signature.assignee_id,
        }),
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


def signature_assignee(db: Session, statement: PaymentBoard):
    failed = db.scalar(select(PaymentSignature).where(
        PaymentSignature.payment_board_id == statement.id,
        PaymentSignature.status == "FAILED",
    ).order_by(PaymentSignature.created_at.desc()))
    if failed:
        return failed.assignee_id
    step = db.scalar(select(PaymentWorkflowStep).where(
        PaymentWorkflowStep.workflow_id == select(PaymentWorkflow.id).where(
            PaymentWorkflow.payment_board_id == statement.id
        ).scalar_subquery(),
        PaymentWorkflowStep.action == "APPROVED",
    ).order_by(PaymentWorkflowStep.completed_at.desc()))
    return step.assignee_id if step else None


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
        reference_id=reference_id or payload.reference_id or payload.period_id,
        created_by=created_by,
        status="CALCULATED",
    )
    statement.items = make_items(items)
    statement.sub_total, statement.tax_amount, statement.total_amount = calculate_totals(statement)
    return statement


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
    add_event(db, f"payment.{next_status.lower()}", statement)
    if next_status == "SUBMITTED":
        create_workflow(db, statement, assignees or [])
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/stats")
def payment_stats(db: Session = Depends(get_db)):
    rows = db.execute(select(PaymentBoard.status, func.count(PaymentBoard.id)).group_by(PaymentBoard.status)).all()
    values = {name.lower(): count for name, count in rows}
    return {"total": sum(values.values()), "draft": values.get("draft", 0), "submitted": values.get("submitted", 0), "approved": values.get("approved", 0), "signed": values.get("signed", 0), "issued": values.get("issued", 0)}


@router.get("/payments/production-periods")
def production_periods(contract_id: str, db: Session = Depends(get_db)):
    rows = call_json(
        "GET",
        f"{PRODUCTION_SERVICE_URL}/api/v1/internal/volumes/billing-sync",
    )
    rows = [row for row in rows if str(row.get("contract_id")) == contract_id]
    periods = {}
    for row in rows:
        period_id = row.get("period_key")
        if not period_id:
            continue
        period = periods.setdefault(period_id, {"period_id": period_id, "locked": True})
        period["locked"] = period["locked"] and row.get("is_locked") and row.get("period_status") == "LOCKED"

    result = []
    for period_id, period in sorted(periods.items()):
        year, month = (int(value) for value in period_id.split("-"))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        billed = db.scalar(select(PaymentBoard.id).where(
            PaymentBoard.contract_id == contract_id,
            PaymentBoard.period_start == start,
            PaymentBoard.period_end == end,
            PaymentBoard.status.not_in({"CANCELLED", "REJECTED"}),
        ).limit(1)) is not None
        if period["locked"]:
            result.append({
                "period_id": period_id,
                "from_date": start.isoformat(),
                "to_date": end.isoformat(),
                "status": "LOCKED",
                "is_billed": billed,
            })
    return [period for period in result if not period["is_billed"]]


@router.get("/payments/production-volumes")
def production_volumes(contract_id: str, period_key: str):
    rows = call_json(
        "GET",
        f"{PRODUCTION_SERVICE_URL}/api/v1/internal/volumes/billing-sync",
        query={"period_key": period_key},
    )
    return [
        row for row in rows
        if str(row.get("contract_id")) == contract_id
        and row.get("period_key") == period_key
        and row.get("is_locked")
        and row.get("period_status") == "LOCKED"
    ]


@router.get("/payments")
def list_payments(status_filter: str | None = Query(None, alias="status"), search: str | None = None, db: Session = Depends(get_db)):
    query = select(PaymentBoard).order_by(PaymentBoard.created_at.desc())
    if status_filter and status_filter != "Tất cả":
        query = query.where(PaymentBoard.status == status_filter.upper())
    if search:
        query = query.where(PaymentBoard.code.ilike(f"%{search.strip()}%"))
    items = db.scalars(query).all()
    return {"items": [serialize(item) for item in items], "total": len(items)}


@router.post("/payments", status_code=status.HTTP_201_CREATED)
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
    if key:
        db.add(PaymentIdempotencyKey(key=key, statement_id=statement.id))
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    return serialize(statement)


@router.put("/payments/{payment_id}")
def update_payment(payment_id: str, payload: PaymentBoardInput, request: Request, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.status not in {"DRAFT", "CALCULATED", "RECONCILED", "REVISION_REQUESTED"}:
        raise HTTPException(409, "Bảng thanh toán đã khóa, cần tạo hồ sơ điều chỉnh")
    items = validate_payment_sources(payload, request.headers.get("Authorization"))
    statement.customer_id = payload.customer_id
    statement.contract_id = payload.contract_id
    statement.price_table_id = payload.price_table_id
    statement.period_start = payload.period_start
    statement.period_end = payload.period_end
    statement.tax_percent = payload.tax_percent
    statement.reference_id = payload.reference_id or payload.period_id
    statement.items = make_items(items)
    statement.status = "CALCULATED"
    statement.sub_total, statement.tax_amount, statement.total_amount = calculate_totals(statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.post("/payments/{payment_id}/reconcile")
def reconcile(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    return change_status(payment_id, "RECONCILED", payload, db, request.headers.get("X-User", "STAFF"))


@router.post("/payments/{payment_id}/submit")
def submit(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    assignees = [value.strip() for value in request.headers.get("X-Approval-Assignees", "").split(",") if value.strip()]
    return change_status(payment_id, "SUBMITTED", payload, db, request.headers.get("X-User", "STAFF"), assignees)


@router.post("/payments/{payment_id}/approve")
def approve(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    return change_status(payment_id, "APPROVED", payload, db, request.headers.get("X-User", "MANAGER"))


@router.post("/payments/{payment_id}/reject")
def reject(payment_id: str, payload: ActionInput, request: Request, db: Session = Depends(get_db)):
    return change_status(payment_id, "REJECTED", payload, db, request.headers.get("X-User", "MANAGER"))


@router.post("/payments/{payment_id}/request-revision")
def request_revision(payment_id: str, payload: ActionInput, request: Request, db: Session = Depends(get_db)):
    return change_status(payment_id, "REVISION_REQUESTED", payload, db, request.headers.get("X-User", "MANAGER"))


@router.post("/payments/{payment_id}/send-sign")
def send_sign(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement or statement.status not in {"APPROVED", "SIGN_FAILED"}:
        raise HTTPException(409, "Chỉ bảng thanh toán đã duyệt mới được gửi ký")
    assignee_id = signature_assignee(db, statement)
    actor = request.headers.get("X-User", "")
    if not assignee_id or actor != assignee_id:
        raise HTTPException(403, "Bạn không phải người được giao ký hồ sơ này")
    signature = PaymentSignature(payment_board_id=statement.id, assignee_id=assignee_id, status="PENDING")
    db.add(signature)
    db.flush()
    statement.status = "PENDING_SIGN"
    add_signing_event(db, signature)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/{payment_id}/signatures")
def get_signatures(payment_id: str, db: Session = Depends(get_db)):
    if not db.get(PaymentBoard, payment_id):
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    rows = db.scalars(select(PaymentSignature).where(
        PaymentSignature.payment_board_id == payment_id
    ).order_by(PaymentSignature.created_at.desc())).all()
    return [{
        "id": row.id,
        "paymentBoardId": row.payment_board_id,
        "assigneeId": row.assignee_id,
        "status": row.status,
        "createdAt": row.created_at.isoformat(),
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
    } for row in rows]


@router.post("/payments/{payment_id}/issue")
def issue_payment(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.status != "SIGNED":
        raise HTTPException(409, "Chỉ bảng thanh toán đã ký mới được phát hành")
    statement.status = "ISSUED"
    add_event(db, "payment.issued", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.post("/payments/{payment_id}/cancel-sign")
def cancel_sign(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement or statement.status not in {"PENDING_SIGN", "SIGNING"}:
        raise HTTPException(409, "Chỉ phiên ký đang xử lý mới được hủy")
    signature = db.scalar(select(PaymentSignature).where(
        PaymentSignature.payment_board_id == payment_id,
        PaymentSignature.status.in_(["PENDING", "SIGNING"]),
    ).order_by(PaymentSignature.created_at.desc()).with_for_update())
    if not signature:
        raise HTTPException(409, "Không tìm thấy phiên ký đang xử lý")
    signature.status = "CANCELLED"
    signature.resolved_at = datetime.utcnow()
    statement.status = "APPROVED"
    add_event(db, "payment.sign_cancelled", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/{payment_id}/workflow")
def get_workflow(payment_id: str, db: Session = Depends(get_db)):
    workflow = db.scalar(select(PaymentWorkflow).where(PaymentWorkflow.payment_board_id == payment_id))
    if not workflow:
        if not db.get(PaymentBoard, payment_id):
            raise HTTPException(404, "Không tìm thấy bảng thanh toán")
        return {"id": None, "paymentBoardId": payment_id, "status": "NOT_STARTED", "currentStep": None, "steps": []}
    return {"id": workflow.id, "paymentBoardId": workflow.payment_board_id, "status": workflow.status, "currentStep": workflow.current_step, "steps": [{
        "stepNo": step.step_no, "assigneeId": step.assignee_id, "status": step.status,
        "action": step.action, "comment": step.comment,
        "completedAt": step.completed_at.isoformat() if step.completed_at else None,
    } for step in sorted(workflow.steps, key=lambda item: item.step_no)]}


@router.post("/payments/{payment_id}/adjustment", status_code=status.HTTP_201_CREATED)
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
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/outbox/pending")
def pending_outbox(db: Session = Depends(get_db)):
    rows = db.scalars(select(PaymentOutboxEvent).where(PaymentOutboxEvent.published_at.is_(None)).order_by(PaymentOutboxEvent.created_at)).all()
    return {"count": len(rows), "items": [{"id": row.id, "eventType": row.event_type, "aggregateId": row.aggregate_id, "createdAt": row.created_at.isoformat()} for row in rows]}

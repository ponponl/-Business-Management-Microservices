import hashlib
import json
import calendar
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
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
from schemas.payment import ActionInput, CreateAdjustmentRequest, PaymentBoardInput
from services.source_validation import validate_payment_sources
from services.workflow import create_workflow, current_step
from utils.calculations import calculate_totals
from utils.http_client import call_json
from core.security import authenticated_user, require_roles, require_user

PRODUCTION_SERVICE_URL = "http://production-service:8000"

router = APIRouter(
    prefix="/api/v1",
    tags=["payments"],
    dependencies=[Depends(require_user)],
)


def add_event(db: Session, event_type: str, statement: PaymentBoard, extra: dict | None = None):
    event_payload = serialize(statement)
    if extra:
        event_payload.update(extra)
    db.add(PaymentOutboxEvent(
        event_type=event_type,
        aggregate_id=statement.id,
        payload=json.dumps(event_payload, default=str),
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


def request_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def idempotent_result(db: Session, key: str, payload: dict):
    record = db.get(PaymentIdempotencyKey, key)
    if not record:
        return None
    if record.request_hash != request_hash(payload):
        raise HTTPException(409, "Idempotency-Key đã được dùng với dữ liệu khác")
    statement = db.get(PaymentBoard, record.statement_id)
    if not statement:
        raise HTTPException(409, "Idempotency-Key tham chiếu hồ sơ không còn tồn tại")
    return serialize(statement)


def serialize(statement: PaymentBoard):
    subtotal, tax, total = calculate_totals(statement)
    try:
        price_list_usages = json.loads(statement.price_list_usages or "[]")
    except (TypeError, json.JSONDecodeError):
        price_list_usages = []
    return {
        "id": statement.id,
        "code": statement.code,
        "customerId": statement.customer_id,
        "contractId": statement.contract_id,
        "priceTableId": statement.price_table_id,
        "priceListId": statement.price_list_id,
        "priceListVersionId": statement.price_list_version_id,
        "priceListVersionNumber": statement.price_list_version_number,
        "priceListUsages": price_list_usages,
        "periodStart": statement.period_start.isoformat(),
        "periodEnd": statement.period_end.isoformat(),
        "status": statement.status,
        "paymentType": statement.payment_type,
        "parentPaymentId": statement.parent_payment_id,
        "isSuperseded": statement.status == "SUPERSEDED",
        "adjustmentReason": statement.adjustment_reason,
        "adjustments": [{
            "id": adjustment.id,
            "code": adjustment.code,
            "status": adjustment.status,
            "paymentType": adjustment.payment_type,
        } for adjustment in statement.adjustments],
        "taxPercent": float(statement.tax_percent),
        "subTotal": float(subtotal),
        "taxAmount": float(tax),
        "totalAmount": float(total),
        "referenceId": statement.reference_id,
        "createdBy": statement.created_by,
        "createdAt": statement.created_at.isoformat() if statement.created_at else None,
        "items": [{
            "id": item.id,
            "operationDate": item.operation_date.isoformat() if item.operation_date else None,
            "serviceCode": item.service_code,
            "serviceName": item.service_name,
            "unit": item.unit,
            "quantity": float(item.quantity),
            "unitPrice": float(item.unit_price),
            "totalPrice": float(item.total_price),
            "priceListName": item.price_list_name,
            "priceListCode": item.price_list_code,
            "priceListVersionId": item.price_list_version_id,
            "priceListVersionNumber": item.price_list_version_number,
        } for item in statement.items],
    }


def ensure_payment_visible(statement: PaymentBoard, user):
    if user.role in {"MANAGER", "DIRECTOR"} and statement.status in {"DRAFT", "CALCULATED", "RECONCILED"}:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")


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
        operation_date=item.get("operation_date"),
        service_name=item["service_name"],
        unit=item["unit"],
        quantity=item["quantity"],
        unit_price=item["unit_price"],
        total_price=item["quantity"] * item["unit_price"],
        price_list_name=item.get("price_list_name"),
        price_list_code=item.get("price_list_code"),
        price_list_version_id=item.get("price_list_version_id"),
        price_list_version_number=item.get("price_list_version_number"),
    ) for item in items]


def create_board(
    payload: PaymentBoardInput,
    items,
    code: str,
    created_by: str,
    reference_id: str | None = None,
    payment_type: str = "STANDARD",
    parent_payment_id: str | None = None,
    status: str = "CALCULATED",
    adjustment_reason: str | None = None,
    price_list_id: str | None = None,
    price_list_version_id: str | None = None,
    price_list_version_number: str | None = None,
    price_list_usages: list[dict] | None = None,
):
    statement = PaymentBoard(
        code=code,
        customer_id=payload.customer_id,
        contract_id=payload.contract_id,
        price_table_id=payload.price_table_id,
        price_list_id=price_list_id,
        price_list_version_id=price_list_version_id,
        price_list_version_number=price_list_version_number,
        price_list_usages=json.dumps(price_list_usages or [], default=str),
        period_start=payload.period_start,
        period_end=payload.period_end,
        tax_percent=payload.tax_percent,
        reference_id=reference_id or payload.reference_id or payload.period_id,
        created_by=created_by,
        status=status,
        payment_type=payment_type,
        parent_payment_id=parent_payment_id,
        adjustment_reason=adjustment_reason,
    )
    statement.items = make_items(items)
    statement.sub_total, statement.tax_amount, statement.total_amount = calculate_totals(statement)
    return statement


def change_status(
    payment_id: str,
    next_status: str,
    payload: ActionInput,
    db: Session,
    actor: str,
    assignees: list[str] | None = None,
    authorization: str | None = None,
    idempotency_key: str | None = None,
):
    if not idempotency_key:
        raise HTTPException(400, "Thiếu Idempotency-Key khi thực hiện thao tác")
    action_payload = {
        "payment_id": payment_id,
        "action": next_status,
        "comment": payload.comment,
        "assignees": assignees or [],
    }
    action_key = f"action:{idempotency_key}"
    replay = idempotent_result(db, action_key, action_payload)
    if replay:
        return replay
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    replay = idempotent_result(db, action_key, action_payload)
    if replay:
        return replay
    allowed = {"RECONCILED": {"DRAFT", "CALCULATED"}, "SUBMITTED": {"RECONCILED"}, "APPROVED": {"SUBMITTED"}, "REJECTED": {"SUBMITTED"}}
    if statement.status not in allowed[next_status]:
        raise HTTPException(409, f"Không thể chuyển từ {statement.status} sang {next_status}")
    subtotal, tax, total = calculate_totals(statement)
    statement.sub_total, statement.tax_amount, statement.total_amount = subtotal, tax, total
    if next_status == "SUBMITTED" and (total < 0 or not statement.items):
        raise HTTPException(422, "Bảng thanh toán phải có dòng dịch vụ và tổng tiền không âm")
    if next_status == "REJECTED" and not payload.comment:
        raise HTTPException(422, "Bắt buộc nhập lý do khi từ chối")
    final_status = next_status
    if next_status in {"APPROVED", "REJECTED"}:
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
        create_workflow(
            db,
            statement,
            assignees or [],
            authorization=authorization,
        )
    db.add(PaymentIdempotencyKey(
        key=action_key,
        statement_id=statement.id,
        request_hash=request_hash(action_payload),
    ))
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/stats")
def payment_stats(request: Request, db: Session = Depends(get_db)):
    user = authenticated_user(request)
    query = select(PaymentBoard.status, func.count(PaymentBoard.id))
    if user.role in {"MANAGER", "DIRECTOR"}:
        query = query.where(PaymentBoard.status.not_in({"DRAFT", "CALCULATED", "RECONCILED"}))
    rows = db.execute(query.group_by(PaymentBoard.status)).all()
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
            PaymentBoard.status.not_in({"CANCELLED", "REJECTED"}),
            or_(
                PaymentBoard.reference_id == period_id,
                (PaymentBoard.period_start == start) & (PaymentBoard.period_end == end),
            ),
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
def list_payments(
    status_filter: str | None = Query(None, alias="status"),
    payment_type: str | None = Query(None, alias="paymentType"),
    include_superseded: bool = Query(True, alias="includeSuperseded"),
    search: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    user = authenticated_user(request)
    query = select(PaymentBoard).order_by(PaymentBoard.created_at.desc())
    if user.role in {"MANAGER", "DIRECTOR"}:
        query = query.where(PaymentBoard.status.not_in({"DRAFT", "CALCULATED", "RECONCILED"}))
    if status_filter and status_filter != "Tất cả":
        query = query.where(PaymentBoard.status == status_filter.upper())
    if payment_type:
        query = query.where(PaymentBoard.payment_type == payment_type.upper())
    if not include_superseded:
        query = query.where(PaymentBoard.status != "SUPERSEDED")
    if search:
        query = query.where(PaymentBoard.code.ilike(f"%{search.strip()}%"))
    items = db.scalars(query).all()
    return {"items": [serialize(item) for item in items], "total": len(items)}


@router.post("/payments", status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentBoardInput, request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, "STAFF")
    key = request.headers.get("Idempotency-Key")
    if not key:
        raise HTTPException(400, "Thiếu Idempotency-Key khi tạo bảng thanh toán")
    payload_data = payload.model_dump(mode="json", by_alias=False)
    replay = idempotent_result(db, key, payload_data)
    if replay:
        return replay
    code = payload.code or f"PAY-{datetime.utcnow():%Y%m%d%H%M%S}"
    if db.scalar(select(PaymentBoard).where(PaymentBoard.code == code)):
        raise HTTPException(409, "Mã bảng thanh toán đã tồn tại")
    validated = validate_payment_sources(payload, request.headers.get("Authorization"))
    statement = create_board(
        payload,
        validated["items"],
        code,
        user.user_id,
        price_list_id=validated["price_list_id"],
        price_list_version_id=validated["price_list_version_id"],
        price_list_version_number=validated["price_list_version_number"],
        price_list_usages=validated["price_list_usages"],
    )
    db.add(statement)
    db.flush()
    db.add(PaymentIdempotencyKey(key=key, statement_id=statement.id, request_hash=request_hash(payload_data)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        replay = idempotent_result(db, key, payload_data)
        if replay:
            return replay
        raise
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    ensure_payment_visible(statement, authenticated_user(request))
    return serialize(statement)


@router.put("/payments/{payment_id}")
def update_payment(payment_id: str, payload: PaymentBoardInput, request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, "STAFF")
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.status not in {"DRAFT", "CALCULATED", "RECONCILED"}:
        raise HTTPException(409, "Bảng thanh toán đã khóa, cần tạo hồ sơ điều chỉnh")
    if statement.created_by not in {user.user_id, user.username}:
        raise HTTPException(403, "Chỉ người tạo bảng thanh toán mới được chỉnh sửa")
    validated = validate_payment_sources(payload, request.headers.get("Authorization"))
    statement.customer_id = payload.customer_id
    statement.contract_id = payload.contract_id
    statement.price_table_id = payload.price_table_id
    statement.price_list_id = validated["price_list_id"]
    statement.price_list_version_id = validated["price_list_version_id"]
    statement.price_list_version_number = validated["price_list_version_number"]
    statement.price_list_usages = json.dumps(validated["price_list_usages"], default=str)
    statement.period_start = payload.period_start
    statement.period_end = payload.period_end
    statement.tax_percent = payload.tax_percent
    statement.reference_id = payload.reference_id or payload.period_id
    statement.items = make_items(validated["items"])
    statement.status = "CALCULATED"
    statement.sub_total, statement.tax_amount, statement.total_amount = calculate_totals(statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.post("/payments/{payment_id}/reconcile")
def reconcile(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    user = require_roles(request, "STAFF")
    return change_status(payment_id, "RECONCILED", payload, db, user.user_id, authorization=request.headers.get("Authorization"), idempotency_key=request.headers.get("Idempotency-Key"))


@router.post("/payments/{payment_id}/submit")
def submit(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    user = require_roles(request, "STAFF")
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.created_by not in {user.user_id, user.username}:
        raise HTTPException(403, "Chỉ người tạo bảng thanh toán mới được trình duyệt")
    assignees = [value.strip() for value in request.headers.get("X-Approval-Assignees", "").split(",") if value.strip()]
    return change_status(payment_id, "SUBMITTED", payload, db, user.user_id, assignees, request.headers.get("Authorization"), request.headers.get("Idempotency-Key"))


@router.post("/payments/{payment_id}/approve")
def approve(payment_id: str, payload: ActionInput = ActionInput(), request: Request = None, db: Session = Depends(get_db)):
    user = require_roles(request, "MANAGER", "DIRECTOR")
    return change_status(payment_id, "APPROVED", payload, db, user.user_id, authorization=request.headers.get("Authorization"), idempotency_key=request.headers.get("Idempotency-Key"))


@router.post("/payments/{payment_id}/reject")
def reject(payment_id: str, payload: ActionInput, request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, "MANAGER", "DIRECTOR")
    return change_status(payment_id, "REJECTED", payload, db, user.user_id, authorization=request.headers.get("Authorization"), idempotency_key=request.headers.get("Idempotency-Key"))


@router.post("/payments/{payment_id}/send-sign")
def send_sign(payment_id: str, request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, "MANAGER", "DIRECTOR")
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement or statement.status not in {"APPROVED", "SIGN_FAILED"}:
        raise HTTPException(409, "Chỉ bảng thanh toán đã duyệt mới được gửi ký")
    assignee_id = signature_assignee(db, statement)
    actor = user.user_id
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
def get_signatures(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    ensure_payment_visible(statement, authenticated_user(request))
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
    user = require_roles(request, "STAFF")
    statement = db.execute(select(PaymentBoard).where(PaymentBoard.id == payment_id).with_for_update()).scalar_one_or_none()
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    if statement.status != "SIGNED":
        raise HTTPException(409, "Chỉ bảng thanh toán đã ký mới được phát hành")
    active_adjustment = db.scalar(select(PaymentBoard.id).where(
        PaymentBoard.parent_payment_id == statement.id,
        PaymentBoard.payment_type == "ADJUSTMENT",
        PaymentBoard.status.not_in({"REJECTED", "CANCELLED"}),
    ).limit(1))
    if active_adjustment:
        raise HTTPException(409, "Bảng thanh toán đã có hồ sơ điều chỉnh và không thể phát hành")
    actor = user.user_id
    if statement.created_by not in {user.user_id, user.username}:
        raise HTTPException(403, "Chỉ người tạo bảng thanh toán mới được phát hành")
    statement.status = "ISSUED"
    add_event(db, "payment.issued", statement, {
        "event": "PAYMENT_ISSUED",
        "eventVersion": 2,
        "priceListUsages": json.loads(statement.price_list_usages or "[]"),
        "occurredAt": datetime.utcnow().isoformat(),
        "issuedBy": actor,
    })
    if statement.payment_type == "ADJUSTMENT" and statement.parent_payment_id:
        parent = db.execute(select(PaymentBoard).where(
            PaymentBoard.id == statement.parent_payment_id
        ).with_for_update()).scalar_one_or_none()
        if parent and parent.status in {"SIGNED", "ISSUED"}:
            parent.status = "SUPERSEDED"
            add_event(db, "payment.superseded", parent)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.post("/payments/{payment_id}/cancel-sign")
def cancel_sign(payment_id: str, request: Request, db: Session = Depends(get_db)):
    authenticated_user(request)
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
def get_workflow(payment_id: str, request: Request, db: Session = Depends(get_db)):
    statement = db.get(PaymentBoard, payment_id)
    if not statement:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán")
    ensure_payment_visible(statement, authenticated_user(request))
    workflow = db.scalar(select(PaymentWorkflow).where(PaymentWorkflow.payment_board_id == payment_id))
    if not workflow:
        return {"id": None, "paymentBoardId": payment_id, "status": "NOT_STARTED", "currentStep": None, "steps": []}
    return {"id": workflow.id, "paymentBoardId": workflow.payment_board_id, "status": workflow.status, "currentStep": workflow.current_step, "steps": [{
        "stepNo": step.step_no, "assigneeId": step.assignee_id, "status": step.status,
        "action": step.action, "comment": step.comment,
        "completedAt": step.completed_at.isoformat() if step.completed_at else None,
    } for step in sorted(workflow.steps, key=lambda item: item.step_no)]}


@router.post("/payments/{payment_id}/adjustments", status_code=status.HTTP_201_CREATED)
@router.post("/payments/{payment_id}/adjustment", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_adjustment(payment_id: str, payload: CreateAdjustmentRequest, request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, "STAFF")
    original = db.execute(select(PaymentBoard).where(
        PaymentBoard.id == payment_id
    ).with_for_update()).scalar_one_or_none()
    if not original:
        raise HTTPException(404, "Không tìm thấy bảng thanh toán gốc")
    if original.status not in {"SUBMITTED", "SIGNED", "ISSUED", "SIGN_FAILED"}:
        raise HTTPException(409, "Chỉ hồ sơ đã trình duyệt hoặc đã ký mới được tạo điều chỉnh")
    existing_adjustment = db.scalar(select(PaymentBoard.id).where(
        PaymentBoard.parent_payment_id == original.id,
        PaymentBoard.payment_type == "ADJUSTMENT",
        PaymentBoard.status.in_({"DRAFT", "SUBMITTED", "APPROVED", "SIGNING", "PENDING_SIGN", "SIGNED", "ISSUED"}),
    ).limit(1))
    if existing_adjustment:
        raise HTTPException(409, "Đã tồn tại hồ sơ điều chỉnh đang xử lý hoặc đã có hiệu lực")
    actor = user.user_id
    if original.created_by not in {user.user_id, user.username}:
        raise HTTPException(403, "Chỉ người tạo bảng thanh toán mới được tạo điều chỉnh")
    adjustment_count = db.scalar(select(func.count(PaymentBoard.id)).where(
        PaymentBoard.parent_payment_id == original.id,
        PaymentBoard.payment_type == "ADJUSTMENT",
    )) or 0
    code = f"{original.code}-ADJ{adjustment_count + 1}"
    if db.scalar(select(PaymentBoard).where(PaymentBoard.code == code)):
        raise HTTPException(409, "Mã bảng điều chỉnh đã tồn tại")
    items = [{
        "service_code": item.service_code,
        "service_name": item.service_name,
        "unit": item.unit,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "price_list_name": item.price_list_name,
        "price_list_code": item.price_list_code,
        "price_list_version_id": item.price_list_version_id,
        "price_list_version_number": item.price_list_version_number,
    } for item in original.items]
    adjustment_payload = PaymentBoardInput(
        customerId=original.customer_id,
        contractId=original.contract_id,
        priceTableId=original.price_table_id,
        periodStart=original.period_start,
        periodEnd=original.period_end,
        taxPercent=original.tax_percent,
        referenceId=original.reference_id,
        periodId=original.period_start.strftime("%Y-%m"),
        items=[{
            "serviceCode": item["service_code"],
            "serviceName": item["service_name"],
            "unit": item["unit"],
            "quantity": item["quantity"],
            "unitPrice": item["unit_price"],
        } for item in items],
    )
    statement = create_board(
        adjustment_payload,
        items,
        code,
        user.user_id,
        original.id,
        payment_type="ADJUSTMENT",
        parent_payment_id=original.id,
        status="DRAFT",
        adjustment_reason=payload.adjustment_reason,
        price_list_id=original.price_list_id,
        price_list_version_id=original.price_list_version_id,
        price_list_version_number=original.price_list_version_number,
        price_list_usages=json.loads(original.price_list_usages or "[]"),
    )
    db.add(statement)
    db.flush()
    add_event(db, "payment.adjustment_created", statement)
    db.commit()
    db.refresh(statement)
    return serialize(statement)


@router.get("/payments/outbox/pending")
def pending_outbox(db: Session = Depends(get_db)):
    rows = db.scalars(select(PaymentOutboxEvent).where(PaymentOutboxEvent.published_at.is_(None)).order_by(PaymentOutboxEvent.created_at)).all()
    return {"count": len(rows), "items": [{"id": row.id, "eventType": row.event_type, "aggregateId": row.aggregate_id, "createdAt": row.created_at.isoformat()} for row in rows]}

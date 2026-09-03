from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.payment import PaymentBoard, PaymentWorkflow, PaymentWorkflowStep
from utils.http_client import call_json

AUTH_USERS_URL = "http://auth-service:8000/api/v1/auth/users"


def create_workflow(
    db: Session,
    statement: PaymentBoard,
    assignees: list[str],
    authorization: str | None = None,
):
    assignees = list(dict.fromkeys(value.strip() for value in assignees if value.strip()))
    if not assignees:
        raise HTTPException(422, "Phải chỉ định ít nhất một người xử lý workflow")
    users = call_json("GET", AUTH_USERS_URL, authorization=authorization)
    users_by_id = {str(user.get("id")): user for user in users}
    invalid_assignees = [assignee for assignee in assignees if assignee not in users_by_id]
    if invalid_assignees:
        raise HTTPException(422, f"Người xử lý không tồn tại: {', '.join(invalid_assignees)}")
    creator_id = str(statement.created_by)
    creator_assigned = [
        assignee for assignee in assignees
        if assignee == creator_id or assignee == str(users_by_id[assignee].get("username", ""))
    ]
    if creator_assigned:
        raise HTTPException(422, "Người tạo bảng thanh toán không được tự phê duyệt hồ sơ")
    unauthorized_assignees = [
        assignee for assignee in assignees
        if str(users_by_id[assignee].get("role", "")).upper() not in {"MANAGER", "DIRECTOR"}
        or not users_by_id[assignee].get("is_active", True)
    ]
    if unauthorized_assignees:
        raise HTTPException(422, "Workflow chỉ được giao cho người duyệt đang hoạt động (MANAGER hoặc DIRECTOR)")
    workflow = db.scalar(select(PaymentWorkflow).where(PaymentWorkflow.payment_board_id == statement.id))
    if workflow:
        workflow.current_step = 1
        workflow.status = "IN_PROGRESS"
        workflow.steps.clear()
    else:
        workflow = PaymentWorkflow(payment_board_id=statement.id)
    workflow.steps = [PaymentWorkflowStep(step_no=index, assignee_id=assignee) for index, assignee in enumerate(assignees, 1)]
    db.add(workflow)


def current_step(db: Session, statement: PaymentBoard):
    workflow = db.scalar(select(PaymentWorkflow).where(PaymentWorkflow.payment_board_id == statement.id))
    if not workflow or workflow.status != "IN_PROGRESS":
        raise HTTPException(409, "Hồ sơ chưa có workflow đang xử lý")
    step = db.scalar(select(PaymentWorkflowStep).where(
        PaymentWorkflowStep.workflow_id == workflow.id,
        PaymentWorkflowStep.step_no == workflow.current_step,
    ).with_for_update())
    if not step or step.status != "PENDING":
        raise HTTPException(409, "Bước phê duyệt hiện tại không hợp lệ")
    return workflow, step

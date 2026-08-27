from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.payment import PaymentBoard, PaymentWorkflow, PaymentWorkflowStep


def create_workflow(db: Session, statement: PaymentBoard, assignees: list[str]):
    assignees = list(dict.fromkeys(value.strip() for value in assignees if value.strip()))
    if not assignees:
        raise HTTPException(422, "Phải chỉ định ít nhất một người xử lý workflow")
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

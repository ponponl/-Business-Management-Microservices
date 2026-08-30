from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_approval import ContractApproval
from app.models.contract_audit import ContractAudit
from app.models.outbox_event import OutboxEvent
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.contract_repository import ContractRepository
from app.services.state_machine import (
    ContractStatus,
    ContractStateMachine,
)


class ApprovalService:

    @staticmethod
    def _load_approval_context(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
    ) -> tuple[Contract, ContractApproval]:
        """Helper gom cụm các invariant chung: Lock & Validate quyền duyệt."""
        # 1. Khóa và kiểm tra Contract
        contract = ContractRepository.get_by_id_for_update(
            db=db,
            contract_id=contract_id,
        )
        if contract is None:
            raise ValueError("CONTRACT_NOT_FOUND")

        if contract.status != ContractStatus.UNDER_REVIEW.value:
            raise ValueError("INVALID_STATE")

        # 2. Khóa và kiểm tra Approval record
        approval = ApprovalRepository.get_current_for_update(
            db=db,
            contract_id=contract_id,
        )
        if approval is None:
            raise ValueError("APPROVAL_NOT_FOUND")

        if approval.status != "PENDING":
            raise ValueError("APPROVAL_ALREADY_PROCESSED")

        # 3. Kiểm tra đúng người được gán duyệt (APR-01)
        if approval.approver_id != actor_id:
            raise ValueError("NOT_ASSIGNED_APPROVER")

        return contract, approval

    @staticmethod
    def start_review(
        db: Session,
        contract_id: UUID,
        approver_id: UUID,
        actor_id: UUID,
    ) -> Contract:
        """Chuyển trạng thái từ SUBMITTED sang UNDER_REVIEW và gán người duyệt."""
        try:
            contract = ContractRepository.get_by_id_for_update(
                db=db,
                contract_id=contract_id,
            )
            if contract is None:
                raise ValueError("CONTRACT_NOT_FOUND")

            if contract.status != ContractStatus.SUBMITTED.value:
                raise ValueError("INVALID_STATE")

            current_approval = ApprovalRepository.get_current(
                db=db,
                contract_id=contract_id,
            )
            if current_approval is not None:
                raise ValueError("APPROVAL_ALREADY_EXISTS")

            previous_status = contract.status
            new_status = ContractStateMachine.transition(
                current_status=ContractStatus(contract.status),
                action="start_review",
            )

            contract.status = new_status.value
            contract.row_version += 1

            approval = ContractApproval(
                contract_id=contract.contract_id,
                step_no=1,
                approver_id=approver_id,
                status="PENDING",
            )
            db.add(approval)

            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="START_REVIEW",
                status_before=previous_status,
                status_after=contract.status,
                note=f"Approval assigned to {approver_id}",
            )
            db.add(audit)

            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_SUBMITTED_FOR_REVIEW",
                payload={
                    "contract_id": str(contract.contract_id),
                    "contract_number": contract.contract_number,
                    "customer_id": str(contract.customer_id),
                    "approver_id": str(approver_id),
                    "step_no": 1,
                    "status": contract.status,
                },
                status="PENDING",
                retry_count=0,
            )
            db.add(outbox_event)

            db.commit()
            db.refresh(contract)
            return contract

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def approve(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        comment: str | None = None,
    ) -> Contract:
        """Duyệt hợp đồng: UNDER_REVIEW -> APPROVED."""
        try:
            # 1. Lock Contract + Approval qua helper
            contract, approval = ApprovalService._load_approval_context(
                db=db,
                contract_id=contract_id,
                actor_id=actor_id,
            )

            # 2. State transition
            new_status = ContractStateMachine.transition(
                current_status=ContractStatus(contract.status),
                action="approve",
            )
            previous_status = contract.status

            # 3. Update Approval
            approval.status = "APPROVED"
            approval.comment = comment

            # 4. Update Contract
            contract.status = new_status.value
            contract.row_version += 1

            # 5. Audit Log
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="APPROVE",
                status_before=previous_status,
                status_after=contract.status,
                note=comment,
            )
            db.add(audit)

            # 6. Outbox Event
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_APPROVED",
                payload={
                    "contract_id": str(contract.contract_id),
                    "contract_number": contract.contract_number,
                    "customer_id": str(contract.customer_id),
                    "version_no": contract.current_version,
                    "approver_id": str(actor_id),
                    "status": contract.status,
                    "comment": comment,
                },
                status="PENDING",
                retry_count=0,
            )
            db.add(outbox_event)

            # 7. Commit & Refresh
            db.commit()
            db.refresh(contract)
            return contract

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def reject(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> Contract:
        """Từ chối hợp đồng: UNDER_REVIEW -> REJECTED (Bắt buộc nhập comment)."""
        if not comment or not comment.strip():
            raise ValueError("COMMENT_REQUIRED")

        try:
            # 1. Lock Contract + Approval qua helper
            contract, approval = ApprovalService._load_approval_context(
                db=db,
                contract_id=contract_id,
                actor_id=actor_id,
            )

            # 2. State transition
            new_status = ContractStateMachine.transition(
                current_status=ContractStatus(contract.status),
                action="reject",
            )
            previous_status = contract.status

            # 3. Update Approval
            approval.status = "REJECTED"
            approval.comment = comment.strip()

            # 4. Update Contract
            contract.status = new_status.value
            contract.row_version += 1

            # 5. Audit Log
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="REJECT",
                status_before=previous_status,
                status_after=contract.status,
                note=comment.strip(),
            )
            db.add(audit)

            # 6. Outbox Event
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_REJECTED",
                payload={
                    "contract_id": str(contract.contract_id),
                    "contract_number": contract.contract_number,
                    "customer_id": str(contract.customer_id),
                    "version_no": contract.current_version,
                    "approver_id": str(actor_id),
                    "status": contract.status,
                    "comment": comment.strip(),
                },
                status="PENDING",
                retry_count=0,
            )
            db.add(outbox_event)

            # 7. Commit & Refresh
            db.commit()
            db.refresh(contract)
            return contract

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def request_revision(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> Contract:
        """Yêu cầu sửa hợp đồng: UNDER_REVIEW -> REVISION_REQUESTED (Bắt buộc nhập comment)."""
        if not comment or not comment.strip():
            raise ValueError("COMMENT_REQUIRED")

        try:
            # 1. Lock Contract + Approval qua helper
            contract, approval = ApprovalService._load_approval_context(
                db=db,
                contract_id=contract_id,
                actor_id=actor_id,
            )

            # 2. State transition
            new_status = ContractStateMachine.transition(
                current_status=ContractStatus(contract.status),
                action="request_revision",
            )
            previous_status = contract.status

            # 3. Update Approval
            approval.status = "REVISION_REQUESTED"
            approval.comment = comment.strip()

            # 4. Update Contract
            contract.status = new_status.value
            contract.row_version += 1

            # 5. Audit Log
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="REQUEST_REVISION",
                status_before=previous_status,
                status_after=contract.status,
                note=comment.strip(),
            )
            db.add(audit)

            # 6. Outbox Event
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_REVISION_REQUESTED",
                payload={
                    "contract_id": str(contract.contract_id),
                    "contract_number": contract.contract_number,
                    "customer_id": str(contract.customer_id),
                    "version_no": contract.current_version,
                    "approver_id": str(actor_id),
                    "status": contract.status,
                    "comment": comment.strip(),
                },
                status="PENDING",
                retry_count=0,
            )
            db.add(outbox_event)

            # 7. Commit & Refresh
            db.commit()
            db.refresh(contract)
            return contract

        except Exception:
            db.rollback()
            raise
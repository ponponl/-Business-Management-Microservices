from uuid import UUID

from app.core.event_builder import build_contract_event
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_approval import ContractApproval
from app.models.contract_audit import ContractAudit
from app.models.outbox_event import OutboxEvent

from app.repositories.approval_repository import (
    ApprovalRepository,
)

from app.repositories.contract_repository import (
    ContractRepository,
)

from app.services.state_machine import (
    ContractStatus,
    ContractStateMachine,
)
from app.services.revision_context import (
    DIRECTOR_REQUEST_REVISION,
    MANAGER_REQUEST_REVISION,
    MANAGER_SEND_REVISION,
)


class ApprovalService:

    @staticmethod
    def _build_action_outbox_event(
        *,
        contract: Contract,
        event_type: str,
        actor_id: UUID,
        actor_role: str,
        approval_round: int,
    ) -> OutboxEvent:
        event = build_contract_event(
            event_name=event_type,
            contract_id=contract.contract_id,
            payload={
                "contract_id": str(contract.contract_id),
                "contract_number": contract.contract_number,
                "customer_id": str(contract.customer_id),
                "current_version": contract.current_version,
                "status": contract.status,
                "actor_id": str(actor_id),
                "actor_role": actor_role,
                "approval_round": approval_round,
            },
        )

        return OutboxEvent(
            aggregate_type="CONTRACT",
            aggregate_id=contract.contract_id,
            event_type=event_type,
            payload=event,
            status="PENDING",
            retry_count=0,
        )

    # =====================================================
    # COMMON APPROVAL CONTEXT
    # =====================================================
    @staticmethod
    def _load_approval_context(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        expected_status: ContractStatus,
    ) -> tuple[Contract, ContractApproval]:

        # 1. Lock Contract
        contract = ContractRepository.get_by_id_for_update(
            db=db,
            contract_id=contract_id,
        )

        if contract is None:
            raise ValueError(
                "CONTRACT_NOT_FOUND"
            )

        # 2. Validate Contract state
        if contract.status != expected_status.value:
            raise ValueError(
                "INVALID_STATE"
            )

        # 3. Resolve the expected step in the latest approval round.
        latest_round = ApprovalRepository.get_latest_round(
            db=db,
            contract_id=contract_id,
        )
        expected_step = (
            1
            if expected_status == ContractStatus.MANAGER_REVIEW
            else 2
        )
        approval = ApprovalRepository.get_by_round_step_for_update(
            db=db,
            contract_id=contract_id,
            approval_round=latest_round,
            step_no=expected_step,
        )

        if approval is None:
            raise ValueError(
                "APPROVAL_NOT_FOUND"
            )

        # 4. Ensure approval is pending
        if approval.status != "PENDING":
            raise ValueError(
                "APPROVAL_ALREADY_PROCESSED"
            )

        # 5. Ensure correct approver
        if approval.approver_id != actor_id:
            raise ValueError(
                "NOT_ASSIGNED_APPROVER"
            )

        return contract, approval

    # =====================================================
    # START REVIEW
    # =====================================================
    @staticmethod
    def start_review(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        actor_role: str,
    ):
        contract = ContractRepository.get_by_id_for_update(
            db,
            contract_id,
        )

        if contract is None:
            raise ValueError("CONTRACT_NOT_FOUND")

        # =========================================================
        # MANAGER START REVIEW
        # SUBMITTED -> MANAGER_REVIEW
        # =========================================================
        if actor_role == "MANAGER":

            if contract.status != ContractStatus.SUBMITTED.value:
                raise ValueError("INVALID_STATE")

            # Không được tồn tại approval đang xử lý
            existing = ApprovalRepository.get_current_for_update(
                db,
                contract_id,
            )

            if existing is not None:
                raise ValueError("APPROVAL_ALREADY_EXISTS")

            latest_round = ApprovalRepository.get_latest_round(
                db,
                contract_id,
            )

            new_round = latest_round + 1

            previous_status = contract.status

            contract.status = ContractStateMachine.transition(
                ContractStatus(contract.status),
                "start_manager_review",
            ).value

            contract.row_version += 1

            approval = ContractApproval(
                contract_id=contract.contract_id,
                approval_round=new_round,
                step_no=1,
                approver_id=actor_id,
                status="PENDING",
            )

            db.add(approval)

            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="START_MANAGER_REVIEW",
                status_before=previous_status,
                status_after=contract.status,
                note="Manager started contract review",
            )

            db.add(audit)

            event = build_contract_event(
                event_name="CONTRACT_MANAGER_REVIEW_STARTED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(contract.contract_id),
                    "contract_number": contract.contract_number,
                    "status": contract.status,
                    "approval_round": new_round,
                    "step_no": 1,
                },
            )

            db.add(
                OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type="CONTRACT_MANAGER_REVIEW_STARTED",
                    payload=event,
                    status="PENDING",
                    retry_count=0,
                )
            )

            db.commit()
            db.refresh(contract)

            return contract

        # =========================================================
        # DIRECTOR START REVIEW
        # DIRECTOR_REVIEW -> DIRECTOR_REVIEW
        #
        # Chỉ tạo approval step 2 nếu chưa tồn tại.
        # =========================================================
        if actor_role == "DIRECTOR":

            if contract.status != ContractStatus.DIRECTOR_REVIEW.value:
                raise ValueError("INVALID_STATE")

            latest_round = ApprovalRepository.get_latest_round(
                db,
                contract_id,
            )

            if latest_round <= 0:
                raise ValueError("APPROVAL_NOT_FOUND")

            # Kiểm tra Manager approval step 1
            manager_approval = ApprovalRepository.get_by_round_step(
                db=db,
                contract_id=contract_id,
                approval_round=latest_round,
                step_no=1,
            )

            if manager_approval is None:
                raise ValueError("APPROVAL_NOT_FOUND")

            if manager_approval.status != "APPROVED":
                raise ValueError("MANAGER_APPROVAL_REQUIRED")

            # Kiểm tra Director step 2
            director_approval = ApprovalRepository.get_by_round_step(
                db=db,
                contract_id=contract_id,
                approval_round=latest_round,
                step_no=2,
            )

            # -----------------------------------------------------
            # Chưa có Director approval
            # -> tạo mới
            # -----------------------------------------------------
            if director_approval is None:

                director_approval = ContractApproval(
                    contract_id=contract.contract_id,
                    approval_round=latest_round,
                    step_no=2,
                    approver_id=actor_id,
                    status="PENDING",
                )

                db.add(director_approval)

                audit = ContractAudit(
                    contract_id=contract.contract_id,
                    version_id=None,
                    actor_id=actor_id,
                    action="START_DIRECTOR_REVIEW",
                    status_before=contract.status,
                    status_after=contract.status,
                    note="Director started contract review",
                )

                db.add(audit)

                event = build_contract_event(
                    event_name="CONTRACT_DIRECTOR_REVIEW_STARTED",
                    contract_id=contract.contract_id,
                    payload={
                        "contract_id": str(contract.contract_id),
                        "contract_number": contract.contract_number,
                        "status": contract.status,
                        "approval_round": latest_round,
                        "step_no": 2,
                    },
                )

                db.add(
                    OutboxEvent(
                        aggregate_type="CONTRACT",
                        aggregate_id=contract.contract_id,
                        event_type="CONTRACT_DIRECTOR_REVIEW_STARTED",
                        payload=event,
                        status="PENDING",
                        retry_count=0,
                    )
                )

                db.commit()
                db.refresh(contract)

                return contract

            # -----------------------------------------------------
            # Director approval đã tồn tại
            # -----------------------------------------------------

            # Cùng Director và vẫn đang PENDING
            if (
                director_approval.approver_id == actor_id
                and director_approval.status == "PENDING"
            ):
                # Start review là idempotent
                return contract

            # Director đã request revision
            if director_approval.status == "REVISION_REQUESTED":
                raise ValueError("REVISION_ALREADY_REQUESTED")

            # Approval đã xử lý rồi
            raise ValueError("APPROVAL_ALREADY_EXISTS")

        raise ValueError("FORBIDDEN")

    # =====================================================
    # APPROVE
    # =====================================================
    @staticmethod
    def approve(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        actor_role: str,
        comment: str | None = None,
    ) -> Contract:

        try:

            # =================================================
            # MANAGER APPROVE
            # MANAGER_REVIEW -> DIRECTOR_REVIEW
            # =================================================
            if actor_role == "MANAGER":

                contract, approval = (
                    ApprovalService._load_approval_context(
                        db=db,
                        contract_id=contract_id,
                        actor_id=actor_id,
                        expected_status=(
                            ContractStatus.MANAGER_REVIEW
                        ),
                    )
                )

                previous_status = contract.status

                new_status = (
                    ContractStateMachine.transition(
                        current_status=ContractStatus(
                            contract.status
                        ),
                        action="approve_manager",
                    )
                )

                # Approval
                approval.status = "APPROVED"
                approval.comment = comment

                # Contract
                contract.status = new_status.value
                contract.row_version += 1

                # Audit
                audit = ContractAudit(
                    contract_id=contract.contract_id,
                    version_id=None,
                    actor_id=actor_id,
                    action="MANAGER_APPROVE",
                    status_before=previous_status,
                    status_after=contract.status,
                    note=comment,
                )

                db.add(audit)

                # Outbox
                outbox_event = ApprovalService._build_action_outbox_event(
                    contract=contract,
                    event_type="CONTRACT_MANAGER_APPROVED",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    approval_round=approval.approval_round,
                )

                db.add(outbox_event)

                db.commit()
                db.refresh(contract)

                return contract

            # =================================================
            # DIRECTOR APPROVE
            # DIRECTOR_REVIEW -> APPROVED
            # =================================================
            if actor_role == "DIRECTOR":

                contract, approval = (
                    ApprovalService._load_approval_context(
                        db=db,
                        contract_id=contract_id,
                        actor_id=actor_id,
                        expected_status=(
                            ContractStatus.DIRECTOR_REVIEW
                        ),
                    )
                )

                previous_status = contract.status

                new_status = (
                    ContractStateMachine.transition(
                        current_status=ContractStatus(
                            contract.status
                        ),
                        action="approve_director",
                    )
                )

                # Approval
                approval.status = "APPROVED"
                approval.comment = comment

                # Contract
                contract.status = new_status.value
                contract.row_version += 1

                # Audit
                audit = ContractAudit(
                    contract_id=contract.contract_id,
                    version_id=None,
                    actor_id=actor_id,
                    action="DIRECTOR_APPROVE",
                    status_before=previous_status,
                    status_after=contract.status,
                    note=comment,
                )

                db.add(audit)

                # Outbox
                outbox_event = ApprovalService._build_action_outbox_event(
                    contract=contract,
                    event_type="CONTRACT_DIRECTOR_APPROVED",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    approval_round=approval.approval_round,
                )

                db.add(outbox_event)

                db.commit()
                db.refresh(contract)

                return contract

            raise ValueError(
                "FORBIDDEN"
            )

        except Exception:
            db.rollback()
            raise

    # =====================================================
    # REJECT
    # =====================================================
    @staticmethod
    def reject(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        actor_role: str,
        comment: str | None,
    ) -> Contract:

        if not comment or not comment.strip():
            raise ValueError(
                "COMMENT_REQUIRED"
            )

        try:

            if actor_role == "MANAGER":
                expected_status = (
                    ContractStatus.MANAGER_REVIEW
                )

            elif actor_role == "DIRECTOR":
                expected_status = (
                    ContractStatus.DIRECTOR_REVIEW
                )

            else:
                raise ValueError(
                    "FORBIDDEN"
                )

            contract, approval = (
                ApprovalService._load_approval_context(
                    db=db,
                    contract_id=contract_id,
                    actor_id=actor_id,
                    expected_status=expected_status,
                )
            )

            previous_status = contract.status

            new_status = (
                ContractStateMachine.transition(
                    current_status=ContractStatus(
                        contract.status
                    ),
                    action="reject",
                )
            )

            approval.status = "REJECTED"
            approval.comment = comment.strip()

            contract.status = new_status.value
            contract.row_version += 1

            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action=(
                    "MANAGER_REJECT"
                    if actor_role == "MANAGER"
                    else "DIRECTOR_REJECT"
                ),
                status_before=previous_status,
                status_after=contract.status,
                note=comment.strip(),
            )

            db.add(audit)

            event_type = (
                "CONTRACT_MANAGER_REJECTED"
                if actor_role == "MANAGER"
                else "CONTRACT_DIRECTOR_REJECTED"
            )
            outbox_event = ApprovalService._build_action_outbox_event(
                contract=contract,
                event_type=event_type,
                actor_id=actor_id,
                actor_role=actor_role,
                approval_round=approval.approval_round,
            )

            db.add(outbox_event)

            db.commit()
            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise

    # =====================================================
    # REQUEST REVISION
    # =====================================================
    @staticmethod
    def request_revision(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        actor_role: str,
        comment: str,
    ):
        if not comment or not comment.strip():
            raise ValueError("COMMENT_REQUIRED")

        # -------------------------------------------------
        # Load contract + lock
        # -------------------------------------------------
        contract = ContractRepository.get_by_id_for_update(
            db,
            contract_id,
        )

        if contract is None:
            raise ValueError("CONTRACT_NOT_FOUND")

        # -------------------------------------------------
        # Load current version
        # -------------------------------------------------
        version = ContractRepository.get_current_version(
            db,
            contract,
        )

        if version is None:
            raise ValueError("CURRENT_VERSION_NOT_FOUND")

        # =================================================
        # MANAGER REQUEST REVISION
        # MANAGER_REVIEW -> REVISION_REQUESTED
        # =================================================
        if actor_role == "MANAGER":

            if contract.status != ContractStatus.MANAGER_REVIEW.value:
                raise ValueError("INVALID_STATE")

            latest_round = ApprovalRepository.get_latest_round(
                db,
                contract_id,
            )
            approval = ApprovalRepository.get_by_round_step_for_update(
                db=db,
                contract_id=contract_id,
                approval_round=latest_round,
                step_no=1,
            )

            if approval is None:
                raise ValueError("APPROVAL_NOT_FOUND")

            if approval.status != "PENDING":
                raise ValueError("APPROVAL_ALREADY_PROCESSED")

            if approval.approver_id != actor_id:
                raise ValueError("NOT_ASSIGNED_APPROVER")

            previous_status = contract.status

            # Approval record
            approval.status = "REVISION_REQUESTED"
            approval.comment = comment.strip()

            # State transition
            contract.status = ContractStateMachine.transition(
                ContractStatus(contract.status),
                "request_revision",
            ).value

            contract.row_version += 1

            # Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,

                # IMPORTANT:
                # dùng UUID của version
                version_id=version.version_id,

                actor_id=actor_id,
                action=MANAGER_REQUEST_REVISION,
                status_before=previous_status,
                status_after=contract.status,
                note=comment.strip(),
            )

            db.add(audit)

            db.add(
                ApprovalService._build_action_outbox_event(
                    contract=contract,
                    event_type="CONTRACT_MANAGER_REVISION_REQUESTED",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    approval_round=approval.approval_round,
                )
            )

            db.commit()
            db.refresh(contract)

            return contract

        # =================================================
        # DIRECTOR REQUEST REVISION
        #
        # DIRECTOR_REVIEW
        #       ↓
        # DIRECTOR_REVIEW
        #
        # Status KHÔNG ĐỔI
        # Manager sẽ xử lý bước tiếp theo
        # =================================================
        if actor_role == "DIRECTOR":

            if contract.status != ContractStatus.DIRECTOR_REVIEW.value:
                raise ValueError("INVALID_STATE")

            latest_round = ApprovalRepository.get_latest_round(
                db,
                contract_id,
            )
            approval = ApprovalRepository.get_by_round_step_for_update(
                db=db,
                contract_id=contract_id,
                approval_round=latest_round,
                step_no=2,
            )

            if approval is None:
                raise ValueError("APPROVAL_NOT_FOUND")

            if approval.status != "PENDING":
                raise ValueError("APPROVAL_ALREADY_PROCESSED")

            if approval.approver_id != actor_id:
                raise ValueError("NOT_ASSIGNED_APPROVER")

            previous_status = contract.status

            # Approval record
            approval.status = "REVISION_REQUESTED"
            approval.comment = comment.strip()

            # IMPORTANT:
            # Director request revision nhưng status vẫn DIRECTOR_REVIEW
            contract.status = previous_status

            contract.row_version += 1

            # Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,

                # IMPORTANT:
                # dùng UUID của version
                version_id=version.version_id,

                actor_id=actor_id,
                action=DIRECTOR_REQUEST_REVISION,
                status_before=previous_status,
                status_after=contract.status,
                note=comment.strip(),
            )

            db.add(audit)

            db.add(
                ApprovalService._build_action_outbox_event(
                    contract=contract,
                    event_type="CONTRACT_DIRECTOR_REVISION_REQUESTED",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    approval_round=approval.approval_round,
                )
            )

            db.commit()
            db.refresh(contract)

            return contract

        raise ValueError("FORBIDDEN")

    # manager gửi lại cho staff sau khi director yêu cầu sửa đổi
    @staticmethod
    def manager_send_revision(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        actor_role: str,
        comment: str,
    ):
        # -------------------------------------------------
        # 1. Validate role
        # -------------------------------------------------
        if actor_role != "MANAGER":
            raise ValueError("FORBIDDEN")

        # -------------------------------------------------
        # 2. Validate comment
        # -------------------------------------------------
        if not comment or not comment.strip():
            raise ValueError("COMMENT_REQUIRED")

        # -------------------------------------------------
        # 3. Lock contract
        # -------------------------------------------------
        contract = ContractRepository.get_by_id_for_update(
            db,
            contract_id,
        )

        if contract is None:
            raise ValueError("CONTRACT_NOT_FOUND")

        # -------------------------------------------------
        # 4. Must still be DIRECTOR_REVIEW
        # -------------------------------------------------
        if contract.status != ContractStatus.DIRECTOR_REVIEW.value:
            raise ValueError("INVALID_STATE")

        # -------------------------------------------------
        # 5. Get current version
        # -------------------------------------------------
        version = ContractRepository.get_current_version(
            db,
            contract,
        )

        if version is None:
            raise ValueError("CURRENT_VERSION_NOT_FOUND")

        # -------------------------------------------------
        # 6. Get latest approval round
        # -------------------------------------------------
        latest_round = ApprovalRepository.get_latest_round(
            db,
            contract_id,
        )

        if latest_round <= 0:
            raise ValueError("APPROVAL_NOT_FOUND")

        # -------------------------------------------------
        # 7. Get Director approval = step 2
        # -------------------------------------------------
        director_approval = ApprovalRepository.get_by_round_step(
            db=db,
            contract_id=contract_id,
            approval_round=latest_round,
            step_no=2,
        )

        if director_approval is None:
            raise ValueError("APPROVAL_NOT_FOUND")

        # Director must have requested revision
        if director_approval.status != "REVISION_REQUESTED":
            raise ValueError("INVALID_REVISION_SOURCE")

        # -------------------------------------------------
        # 8. Find latest Director revision audit
        # -------------------------------------------------
        latest_director_revision = (
            db.query(ContractAudit)
            .filter(
                ContractAudit.contract_id == contract_id,
                ContractAudit.action
                == DIRECTOR_REQUEST_REVISION,
                ContractAudit.version_id == version.version_id,
            )
            .order_by(
                ContractAudit.created_at.desc(),
                ContractAudit.audit_id.desc(),
            )
            .first()
        )

        if latest_director_revision is None:
            raise ValueError("INVALID_REVISION_SOURCE")

        # -------------------------------------------------
        # 9. Prevent duplicate send
        # -------------------------------------------------
        already_sent = (
            db.query(ContractAudit)
            .filter(
                ContractAudit.contract_id == contract_id,
                ContractAudit.action == MANAGER_SEND_REVISION,
                ContractAudit.version_id == version.version_id,
            )
            .first()
        )

        if already_sent is not None:
            raise ValueError("REVISION_ALREADY_SENT")

        # -------------------------------------------------
        # 10. State transition
        # DIRECTOR_REVIEW -> REVISION_REQUESTED
        # -------------------------------------------------
        previous_status = contract.status

        new_status = ContractStateMachine.transition(
            ContractStatus(contract.status),
            "manager_send_revision",
        )

        contract.status = new_status.value
        contract.row_version += 1

        # -------------------------------------------------
        # 11. Audit
        # -------------------------------------------------
        audit = ContractAudit(
            contract_id=contract.contract_id,

            # IMPORTANT:
            # phải dùng UUID
            version_id=version.version_id,

            actor_id=actor_id,
            action=MANAGER_SEND_REVISION,
            status_before=previous_status,
            status_after=contract.status,

            # Đây là lý do MANAGER gửi cho STAFF
            note=comment.strip(),
        )

        db.add(audit)

        db.add(
            ApprovalService._build_action_outbox_event(
                contract=contract,
                event_type="CONTRACT_MANAGER_SEND_REVISION",
                actor_id=actor_id,
                actor_role=actor_role,
                approval_round=latest_round,
            )
        )

        # -------------------------------------------------
        # 13. Commit
        # -------------------------------------------------
        db.commit()
        db.refresh(contract)

        return contract

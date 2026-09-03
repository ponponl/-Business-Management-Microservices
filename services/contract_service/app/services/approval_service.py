from uuid import UUID

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


class ApprovalService:

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

        # 3. Get current pending approval
        approval = (
            ApprovalRepository.get_current_for_update(
                db=db,
                contract_id=contract_id,
            )
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
    ) -> Contract:

        try:
            # 1. Lock Contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db=db,
                    contract_id=contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # =================================================
            # MANAGER START REVIEW
            # SUBMITTED -> MANAGER_REVIEW
            # =================================================
            if (
                contract.status
                == ContractStatus.SUBMITTED.value
            ):

                if actor_role != "MANAGER":
                    raise ValueError(
                        "FORBIDDEN"
                    )

                # Không được có approval đang PENDING
                current_approval = (
                    ApprovalRepository.get_current(
                        db=db,
                        contract_id=contract_id,
                    )
                )

                if current_approval is not None:
                    raise ValueError(
                        "APPROVAL_ALREADY_EXISTS"
                    )

                # 2. Determine new approval round
                latest_round = (
                    ApprovalRepository.get_latest_round(
                        db=db,
                        contract_id=contract_id,
                    )
                )

                new_round = latest_round + 1

                # 3. State transition
                previous_status = contract.status

                new_status = (
                    ContractStateMachine.transition(
                        current_status=ContractStatus(
                            contract.status
                        ),
                        action="start_manager_review",
                    )
                )

                contract.status = new_status.value
                contract.row_version += 1

                # 4. Create Manager approval
                approval = ContractApproval(
                    contract_id=contract.contract_id,
                    approval_round=new_round,
                    step_no=1,
                    approver_id=actor_id,
                    status="PENDING",
                )

                db.add(approval)

                # 5. Audit
                audit = ContractAudit(
                    contract_id=contract.contract_id,
                    version_id=None,
                    actor_id=actor_id,
                    action="START_MANAGER_REVIEW",
                    status_before=previous_status,
                    status_after=contract.status,
                    note=(
                        f"Manager started review "
                        f"(approval round {new_round})"
                    ),
                )

                db.add(audit)

                # 6. Outbox
                outbox_event = OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type=(
                        "CONTRACT_MANAGER_REVIEW_STARTED"
                    ),
                    payload={
                        "contract_id": str(
                            contract.contract_id
                        ),
                        "contract_number":
                            contract.contract_number,
                        "customer_id": str(
                            contract.customer_id
                        ),
                        "approver_id": str(
                            actor_id
                        ),
                        "approver_role": "MANAGER",
                        "approval_round": new_round,
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

            # =================================================
            # DIRECTOR START REVIEW
            # DIRECTOR_REVIEW -> DIRECTOR_REVIEW
            # =================================================
            if (
                contract.status
                == ContractStatus.DIRECTOR_REVIEW.value
            ):

                if actor_role != "DIRECTOR":
                    raise ValueError(
                        "FORBIDDEN"
                    )

                # 2. Get latest approval round
                latest_round = (
                    ApprovalRepository.get_latest_round(
                        db=db,
                        contract_id=contract_id,
                    )
                )

                if latest_round <= 0:
                    raise ValueError(
                        "APPROVAL_NOT_FOUND"
                    )

                # 3. Manager approval in current round
                manager_approval = (
                    ApprovalRepository.get_by_round_step(
                        db=db,
                        contract_id=contract_id,
                        approval_round=latest_round,
                        step_no=1,
                    )
                )

                if manager_approval is None:
                    raise ValueError(
                        "APPROVAL_NOT_FOUND"
                    )

                if manager_approval.status != "APPROVED":
                    raise ValueError(
                        "MANAGER_APPROVAL_REQUIRED"
                    )

                # 4. Ensure Director approval
                # does not already exist in this round
                director_approval = (
                    ApprovalRepository.get_by_round_step(
                        db=db,
                        contract_id=contract_id,
                        approval_round=latest_round,
                        step_no=2,
                    )
                )

                if director_approval is not None:
                    raise ValueError(
                        "APPROVAL_ALREADY_EXISTS"
                    )

                # 5. Create Director approval
                approval = ContractApproval(
                    contract_id=contract.contract_id,
                    approval_round=latest_round,
                    step_no=2,
                    approver_id=actor_id,
                    status="PENDING",
                )

                db.add(approval)

                # 6. Audit
                audit = ContractAudit(
                    contract_id=contract.contract_id,
                    version_id=None,
                    actor_id=actor_id,
                    action="START_DIRECTOR_REVIEW",
                    status_before=contract.status,
                    status_after=contract.status,
                    note=(
                        f"Director started review "
                        f"(approval round {latest_round})"
                    ),
                )

                db.add(audit)

                # 7. Outbox
                outbox_event = OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type=(
                        "CONTRACT_DIRECTOR_REVIEW_STARTED"
                    ),
                    payload={
                        "contract_id": str(
                            contract.contract_id
                        ),
                        "contract_number":
                            contract.contract_number,
                        "customer_id": str(
                            contract.customer_id
                        ),
                        "approver_id": str(
                            actor_id
                        ),
                        "approver_role": "DIRECTOR",
                        "approval_round":
                            latest_round,
                        "step_no": 2,
                        "status": contract.status,
                    },
                    status="PENDING",
                    retry_count=0,
                )

                db.add(outbox_event)

                db.commit()
                db.refresh(contract)

                return contract

            raise ValueError(
                "INVALID_STATE"
            )

        except Exception:
            db.rollback()
            raise

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
                outbox_event = OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type="CONTRACT_MANAGER_APPROVED",
                    payload={
                        "contract_id": str(
                            contract.contract_id
                        ),
                        "contract_number":
                            contract.contract_number,
                        "customer_id": str(
                            contract.customer_id
                        ),
                        "approval_round":
                            approval.approval_round,
                        "step_no":
                            approval.step_no,
                        "approver_id": str(
                            actor_id
                        ),
                        "approver_role": "MANAGER",
                        "status": contract.status,
                        "comment": comment,
                    },
                    status="PENDING",
                    retry_count=0,
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
                outbox_event = OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type="CONTRACT_APPROVED",
                    payload={
                        "contract_id": str(
                            contract.contract_id
                        ),
                        "contract_number":
                            contract.contract_number,
                        "customer_id": str(
                            contract.customer_id
                        ),
                        "approval_round":
                            approval.approval_round,
                        "step_no":
                            approval.step_no,
                        "approver_id": str(
                            actor_id
                        ),
                        "approver_role": "DIRECTOR",
                        "status": contract.status,
                        "comment": comment,
                    },
                    status="PENDING",
                    retry_count=0,
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

            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_REJECTED",
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "approval_round":
                        approval.approval_round,
                    "step_no":
                        approval.step_no,
                    "approver_id": str(
                        actor_id
                    ),
                    "approver_role":
                        actor_role,
                    "status": contract.status,
                    "comment":
                        comment.strip(),
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

    # =====================================================
    # REQUEST REVISION
    # =====================================================
    @staticmethod
    def request_revision(
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
                    action="request_revision",
                )
            )

            approval.status = "REVISION_REQUESTED"
            approval.comment = comment.strip()

            contract.status = new_status.value
            contract.row_version += 1

            audit_action = (
                "MANAGER_REQUEST_REVISION"
                if actor_role == "MANAGER"
                else "DIRECTOR_REQUEST_REVISION"
            )

            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action=audit_action,
                status_before=previous_status,
                status_after=contract.status,
                note=comment.strip(),
            )

            db.add(audit)

            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_REVISION_REQUESTED",
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "approval_round":
                        approval.approval_round,
                    "step_no":
                        approval.step_no,
                    "approver_id": str(
                        actor_id
                    ),
                    "approver_role":
                        actor_role,
                    "status":
                        contract.status,
                    "comment":
                        comment.strip(),
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

    # =====================================================
    # FORWARD DIRECTOR REVISION TO STAFF
    # =====================================================
    @staticmethod
    def forward_revision(
        db: Session,
        contract_id: UUID,
        actor_id: UUID,
        actor_role: str,
    ) -> Contract:

        try:

            # 1. Only Manager can forward
            if actor_role != "MANAGER":
                raise ValueError(
                    "FORBIDDEN"
                )

            # 2. Lock Contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db=db,
                    contract_id=contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 3. Must be in revision requested state
            if (
                contract.status
                != ContractStatus.REVISION_REQUESTED.value
            ):
                raise ValueError(
                    "INVALID_STATE"
                )

            # 4. Get latest approval round
            latest_round = (
                ApprovalRepository.get_latest_round(
                    db=db,
                    contract_id=contract_id,
                )
            )

            if latest_round <= 0:
                raise ValueError(
                    "APPROVAL_NOT_FOUND"
                )

            # 5. Latest approval must be
            # Director revision request
            director_approval = (
                ApprovalRepository.get_by_round_step(
                    db=db,
                    contract_id=contract_id,
                    approval_round=latest_round,
                    step_no=2,
                )
            )

            if director_approval is None:
                raise ValueError(
                    "APPROVAL_NOT_FOUND"
                )

            if director_approval.status != (
                "REVISION_REQUESTED"
            ):
                raise ValueError(
                    "INVALID_REVISION_SOURCE"
                )

            # 6. Check if already forwarded
            already_forwarded = (
                db.query(ContractAudit)
                .filter(
                    ContractAudit.contract_id
                    == contract.contract_id,
                    ContractAudit.action
                    == "MANAGER_FORWARD_REVISION",
                    ContractAudit.created_at
                    > director_approval.updated_at,
                )
                .first()
            )

            if already_forwarded is not None:
                raise ValueError(
                    "REVISION_ALREADY_FORWARDED"
                )

            # 7. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="MANAGER_FORWARD_REVISION",
                status_before=contract.status,
                status_after=contract.status,
                note=(
                    "Manager reviewed Director's "
                    "revision request and forwarded "
                    "it to Staff"
                ),
            )

            db.add(audit)

            # 8. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type=(
                    "CONTRACT_REVISION_FORWARDED_TO_STAFF"
                ),
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "approval_round":
                        latest_round,
                    "requested_by_role":
                        "DIRECTOR",
                    "forwarded_by":
                        str(actor_id),
                    "status":
                        contract.status,
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
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
        """
        Lock Contract + Approval và validate người được assign.
        """

        # 1. Lock Contract
        contract = ContractRepository.get_by_id_for_update(
            db=db,
            contract_id=contract_id,
        )

        if contract is None:
            raise ValueError(
                "CONTRACT_NOT_FOUND"
            )

        # 2. Validate state
        if contract.status != expected_status.value:
            raise ValueError(
                "INVALID_STATE"
            )

        # 3. Lock current approval
        approval = ApprovalRepository.get_current_for_update(
            db=db,
            contract_id=contract_id,
        )

        if approval is None:
            raise ValueError(
                "APPROVAL_NOT_FOUND"
            )

        # 4. Validate approval status
        if approval.status != "PENDING":
            raise ValueError(
                "APPROVAL_ALREADY_PROCESSED"
            )

        # 5. Validate approver
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
            contract = ContractRepository.get_by_id_for_update(
                db=db,
                contract_id=contract_id,
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # =================================================
            # MANAGER START REVIEW
            # SUBMITTED -> MANAGER_REVIEW
            # =================================================
            if contract.status == ContractStatus.SUBMITTED.value:

                if actor_role != "MANAGER":
                    raise ValueError(
                        "FORBIDDEN"
                    )

                # Không được có approval pending
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

                # Tạo Manager approval
                approval = ContractApproval(
                    contract_id=contract.contract_id,
                    step_no=1,
                    approver_id=actor_id,
                    status="PENDING",
                )

                db.add(approval)

                # Audit
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

                # Outbox
                outbox_event = OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type="CONTRACT_MANAGER_REVIEW_STARTED",
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
                        "step_no": 1,
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

            # =================================================
            # DIRECTOR START REVIEW
            # DIRECTOR_REVIEW -> DIRECTOR_REVIEW
            # =================================================
            if contract.status == ContractStatus.DIRECTOR_REVIEW.value:

                if actor_role != "DIRECTOR":
                    raise ValueError(
                        "FORBIDDEN"
                    )

                # Không được có approval pending
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

                # Tạo Director approval
                approval = ContractApproval(
                    contract_id=contract.contract_id,
                    step_no=2,
                    approver_id=actor_id,
                    status="PENDING",
                )

                db.add(approval)

                # Audit
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

                # Outbox
                outbox_event = OutboxEvent(
                    aggregate_type="CONTRACT",
                    aggregate_id=contract.contract_id,
                    event_type="CONTRACT_DIRECTOR_REVIEW_STARTED",
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
                        "step_no": 2,
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
            # MANAGER APPROVAL
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

                # Approval record
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
                        "version_no":
                            contract.current_version,
                        "approver_id": str(
                            actor_id
                        ),
                        "status":
                            contract.status,
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
            # DIRECTOR APPROVAL
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

                # Approval record
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
                        "version_no":
                            contract.current_version,
                        "approver_id": str(
                            actor_id
                        ),
                        "status":
                            contract.status,
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

            expected_status = None

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
                    "version_no":
                        contract.current_version,
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

            expected_status = None

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

            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action=(
                    "MANAGER_REQUEST_REVISION"
                    if actor_role == "MANAGER"
                    else "DIRECTOR_REQUEST_REVISION"
                ),
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
                    "version_no":
                        contract.current_version,
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
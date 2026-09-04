from dataclasses import dataclass

from app.models.contract import Contract
from app.models.contract_audit import ContractAudit


MANAGER_REQUEST_REVISION = "MANAGER_REQUEST_REVISION"
DIRECTOR_REQUEST_REVISION = "DIRECTOR_REQUEST_REVISION"
MANAGER_SEND_REVISION = "MANAGER_SEND_REVISION"

REVISION_REQUEST_ACTIONS = {
    MANAGER_REQUEST_REVISION,
    DIRECTOR_REQUEST_REVISION,
}


def _audit_sort_key(audit: ContractAudit):
    return audit.created_at, str(audit.audit_id)


@dataclass(frozen=True)
class RevisionContext:
    approval_round: int | None
    request_audit: ContractAudit
    manager_send_audit: ContractAudit | None = None

    @property
    def source(self) -> str:
        return self.request_audit.action

    def to_metadata(self) -> dict:
        manager_request_reason = (
            self.request_audit.note
            if self.source == MANAGER_REQUEST_REVISION
            else None
        )
        director_request_reason = (
            self.request_audit.note
            if self.source == DIRECTOR_REQUEST_REVISION
            else None
        )
        manager_send_reason = (
            self.manager_send_audit.note
            if self.manager_send_audit is not None
            else None
        )

        if self.source == MANAGER_REQUEST_REVISION:
            staff_reason = manager_request_reason
            manager_reason = manager_request_reason
            director_reason = None
            staff_source = "MANAGER"
            manager_source = "MANAGER"
            director_source = None
        else:
            staff_reason = manager_send_reason
            staff_source = "MANAGER" if manager_send_reason else None
            manager_reason = manager_send_reason or director_request_reason
            manager_source = "MANAGER" if manager_send_reason else "DIRECTOR"
            director_reason = director_request_reason
            director_source = "DIRECTOR"

        return {
            "revision_round": self.approval_round,
            "revision_source": self.source,
            "manager_revision_reason": manager_request_reason,
            "director_revision_reason": director_request_reason,
            "manager_send_revision_reason": manager_send_reason,
            "revision_reason_for_staff": staff_reason,
            "revision_reason_source_for_staff": staff_source,
            "revision_reason_for_manager": manager_reason,
            "revision_reason_source_for_manager": manager_source,
            "revision_reason_for_director": director_reason,
            "revision_reason_source_for_director": director_source,
        }


def empty_revision_metadata() -> dict:
    return {
        "revision_round": None,
        "revision_source": None,
        "manager_revision_reason": None,
        "director_revision_reason": None,
        "manager_send_revision_reason": None,
        "revision_reason_for_staff": None,
        "revision_reason_source_for_staff": None,
        "revision_reason_for_manager": None,
        "revision_reason_source_for_manager": None,
        "revision_reason_for_director": None,
        "revision_reason_source_for_director": None,
    }


def get_latest_revision_context(
    contract: Contract,
) -> RevisionContext | None:
    audits = list(getattr(contract, "audits", []) or [])
    approvals = list(getattr(contract, "approval_records", []) or [])
    version_numbers = {
        version.version_id: version.version_no
        for version in (getattr(contract, "versions", []) or [])
    }

    revision_requests = [
        audit
        for audit in audits
        if audit.action in REVISION_REQUEST_ACTIONS
    ]
    if not revision_requests:
        return None

    latest_request = max(
        revision_requests,
        key=lambda audit: (
            version_numbers.get(getattr(audit, "version_id", None), -1),
            *_audit_sort_key(audit),
        ),
    )

    expected_step = 1 if latest_request.action == MANAGER_REQUEST_REVISION else 2
    matching_rounds = [
        approval.approval_round
        for approval in approvals
        if (
            approval.step_no == expected_step
            and approval.status == "REVISION_REQUESTED"
        )
    ]
    if matching_rounds:
        revision_round = max(matching_rounds)
    else:
        revision_round = max(
            (
                approval.approval_round
                for approval in approvals
                if approval.created_at <= latest_request.created_at
            ),
            default=None,
        )

    manager_send_audit = None
    if latest_request.action == DIRECTOR_REQUEST_REVISION:
        sends = [
            audit
            for audit in audits
            if (
                audit.action == MANAGER_SEND_REVISION
                and getattr(audit, "version_id", None)
                == getattr(latest_request, "version_id", None)
            )
        ]
        manager_send_audit = max(sends, key=_audit_sort_key, default=None)

    return RevisionContext(
        approval_round=revision_round,
        request_audit=latest_request,
        manager_send_audit=manager_send_audit,
    )


def get_revision_metadata(contract: Contract) -> dict:
    context = get_latest_revision_context(contract)
    if context is None:
        return empty_revision_metadata()
    return context.to_metadata()


def get_current_approval_metadata(contract: Contract) -> dict:
    approvals = list(getattr(contract, "approval_records", []) or [])
    current_round = max(
        (approval.approval_round for approval in approvals),
        default=None,
    )
    director_approval = max(
        (
            approval
            for approval in approvals
            if (
                approval.approval_round == current_round
                and approval.step_no == 2
            )
        ),
        key=lambda approval: (
            approval.updated_at or approval.created_at,
            str(approval.approval_id),
        ),
        default=None,
    )
    return {
        "current_approval_round": current_round,
        "director_approval_status": (
            director_approval.status if director_approval else None
        ),
    }

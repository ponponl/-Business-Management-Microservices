from enum import Enum


class ContractStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    MANAGER_REVIEW = "MANAGER_REVIEW"
    DIRECTOR_REVIEW = "DIRECTOR_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    REVISION_REQUESTED = "REVISION_REQUESTED"


class ContractStateMachine:

    TRANSITIONS = {
        ContractStatus.DRAFT: {
            "submit": ContractStatus.SUBMITTED,
            "cancel": ContractStatus.CANCELLED,
        },

        ContractStatus.SUBMITTED: {
            "start_manager_review": ContractStatus.MANAGER_REVIEW,
            "cancel": ContractStatus.CANCELLED,
        },

        ContractStatus.REVISION_REQUESTED: {
            "submit": ContractStatus.SUBMITTED,
        },

        ContractStatus.MANAGER_REVIEW: {
            "approve_manager": ContractStatus.DIRECTOR_REVIEW,
            "reject": ContractStatus.REJECTED,
            "request_revision": ContractStatus.REVISION_REQUESTED,
        },

        ContractStatus.DIRECTOR_REVIEW: {
            "approve_director": ContractStatus.APPROVED,
            "reject": ContractStatus.REJECTED,
            "director_request_revision": ContractStatus.DIRECTOR_REVIEW,
            "manager_send_revision": ContractStatus.REVISION_REQUESTED,
        },
        
        ContractStatus.APPROVED: {
            "activate": ContractStatus.ACTIVE,
        },

        ContractStatus.ACTIVE: {
            "expire": ContractStatus.EXPIRED,
        },
    }

    @classmethod
    def can_transition(
        cls,
        current_status: ContractStatus,
        action: str,
    ) -> bool:
        return action in cls.TRANSITIONS.get(
            current_status,
            {},
        )

    @classmethod
    def transition(
        cls,
        current_status: ContractStatus,
        action: str,
    ) -> ContractStatus:

        if not cls.can_transition(
            current_status,
            action,
        ):
            raise ValueError(
                f"Invalid transition: "
                f"{current_status.value} -> {action}"
            )

        return cls.TRANSITIONS[
            current_status
        ][action]

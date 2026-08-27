from enum import Enum


class ContractStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
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

        ContractStatus.REVISION_REQUESTED: {
            "submit": ContractStatus.SUBMITTED,
        },

        ContractStatus.SUBMITTED: {
            "start_review": ContractStatus.UNDER_REVIEW,
        },

        ContractStatus.UNDER_REVIEW: {
            "approve": ContractStatus.APPROVED,
            "reject": ContractStatus.REJECTED,
            "request_revision": ContractStatus.REVISION_REQUESTED,
        },

        ContractStatus.APPROVED: {
            "activate": ContractStatus.ACTIVE,
        },

        ContractStatus.ACTIVE: {
            "cancel": ContractStatus.CANCELLED,
            "expire": ContractStatus.EXPIRED,
        },
    }

    @classmethod
    def can_transition(
        cls,
        current_status: ContractStatus,
        action: str,
    ) -> bool:
        return action in cls.TRANSITIONS.get(current_status, {})

    @classmethod
    def transition(
        cls,
        current_status: ContractStatus,
        action: str,
    ) -> ContractStatus:
        if not cls.can_transition(current_status, action):
            raise ValueError(
                f"Invalid transition: {current_status.value} -> {action}"
            )

        return cls.TRANSITIONS[current_status][action]
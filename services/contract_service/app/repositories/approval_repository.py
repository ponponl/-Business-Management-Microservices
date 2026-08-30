from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contract_approval import (
    ContractApproval,
)


class ApprovalRepository:

    @staticmethod
    def get_current(
        db: Session,
        contract_id: UUID,
    ) -> ContractApproval | None:

        return (
            db.query(ContractApproval)
            .filter(
                ContractApproval.contract_id
                == contract_id,

                ContractApproval.status
                == "PENDING",
            )
            .order_by(
                ContractApproval.step_no.desc()
            )
            .first()
        )

    @staticmethod
    def get_current_for_update(
        db: Session,
        contract_id: UUID,
    ) -> ContractApproval | None:

        return (
            db.query(ContractApproval)
            .filter(
                ContractApproval.contract_id
                == contract_id,

                ContractApproval.status
                == "PENDING",
            )
            .order_by(
                ContractApproval.step_no.desc()
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        approval: ContractApproval,
    ) -> ContractApproval:

        db.add(approval)

        return approval
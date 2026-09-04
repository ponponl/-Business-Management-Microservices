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
                ContractApproval.contract_id == contract_id,
                ContractApproval.status == "PENDING",
            )
            .order_by(
                ContractApproval.approval_round.desc(),
                ContractApproval.step_no.desc(),
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
                ContractApproval.contract_id == contract_id,
                ContractApproval.status == "PENDING",
            )
            .order_by(
                ContractApproval.approval_round.desc(),
                ContractApproval.step_no.desc(),
            )
            .with_for_update()
            .first()
        )
    
    @staticmethod
    def get_latest_round(
        db: Session,
        contract_id: UUID,
    ) -> int:

        result = (
            db.query(ContractApproval.approval_round)
            .filter(
                ContractApproval.contract_id == contract_id
            )
            .order_by(
                ContractApproval.approval_round.desc()
            )
            .first()
        )

        if result is None:
            return 0

        return result[0]
    
    
    @staticmethod
    def get_by_round_step(
        db: Session,
        contract_id: UUID,
        approval_round: int,
        step_no: int,
    ) -> ContractApproval | None:

        return (
            db.query(ContractApproval)
            .filter(
                ContractApproval.contract_id == contract_id,
                ContractApproval.approval_round == approval_round,
                ContractApproval.step_no == step_no,
            )
            .first()
        )

    @staticmethod
    def get_by_round_step_for_update(
        db: Session,
        contract_id: UUID,
        approval_round: int,
        step_no: int,
    ) -> ContractApproval | None:

        return (
            db.query(ContractApproval)
            .filter(
                ContractApproval.contract_id == contract_id,
                ContractApproval.approval_round == approval_round,
                ContractApproval.step_no == step_no,
            )
            .with_for_update()
            .first()
        )
        
    @staticmethod
    def get_all_by_contract(
        db: Session,
        contract_id: UUID,
    ) -> list[ContractApproval]:

        return (
            db.query(ContractApproval)
            .filter(
                ContractApproval.contract_id == contract_id
            )
            .order_by(
                ContractApproval.approval_round.asc(),
                ContractApproval.step_no.asc(),
            )
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        approval: ContractApproval,
    ) -> ContractApproval:

        db.add(approval)

        return approval

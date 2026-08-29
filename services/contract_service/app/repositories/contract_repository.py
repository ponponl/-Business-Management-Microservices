from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_version import ContractVersion


class ContractRepository:

    @staticmethod
    def get_by_id(
        db: Session,
        contract_id: UUID,
    ) -> Contract | None:
        return (
            db.query(Contract)
            .filter(
                Contract.contract_id == contract_id
            )
            .first()
        )
    
    @staticmethod
    def get_by_id_for_update(
        db: Session,
        contract_id: UUID,
    ) -> Contract | None:
        return (
            db.query(Contract)
            .filter(
                Contract.contract_id == contract_id
            )
            .with_for_update()
            .first()
        )
    
    @staticmethod
    def get_version(
        db: Session,
        contract_id: UUID,
        version_no: int,
    ) -> ContractVersion | None:

        return (
            db.query(ContractVersion)
            .filter(
                ContractVersion.contract_id == contract_id,
                ContractVersion.version_no == version_no,
            )
            .first()
        )
    
    @staticmethod
    def get_current_version(
        db: Session,
        contract: Contract,
    ) -> ContractVersion | None:

        return (
            db.query(ContractVersion)
            .filter(
                ContractVersion.contract_id
                == contract.contract_id,

                ContractVersion.version_no
                == contract.current_version,
            )
            .first()
        )
        
    @staticmethod
    def list_contracts(
        db: Session,
        customer_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Contract]:

        query = db.query(Contract)

        if customer_id is not None:
            query = query.filter(
                Contract.customer_id == customer_id
            )

        if status is not None:
            query = query.filter(
                Contract.status == status
            )

        return (
            query
            .order_by(
                Contract.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
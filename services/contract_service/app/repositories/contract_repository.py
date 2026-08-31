from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_version import ContractVersion

from datetime import date


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
    def get_by_number(
        db: Session,
        contract_number: str,
    ) -> Contract | None:

        return (
            db.query(Contract)
            .filter(
                Contract.contract_number
                == contract_number
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
                ContractVersion.contract_id
                == contract_id,
                ContractVersion.version_no
                == version_no,
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

        from sqlalchemy.orm import selectinload
        query = db.query(Contract).options(selectinload(Contract.versions))

        if customer_id is not None:
            query = query.filter(
                Contract.customer_id
                == customer_id
            )

        if status is not None:
            query = query.filter(
                Contract.status
                == status
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

    @staticmethod
    def count_contracts(
        db: Session,
        customer_id: UUID | None = None,
        status: str | None = None,
    ) -> int:

        query = db.query(Contract)

        if customer_id is not None:
            query = query.filter(
                Contract.customer_id
                == customer_id
            )

        if status is not None:
            query = query.filter(
                Contract.status
                == status
            )

        return query.count()
    
    
    # New method to find contracts to activate based on effective date
    @staticmethod
    def find_contracts_to_activate(
        db,
        today: date,
        limit: int = 100,
    ):
        return (
            db.query(Contract)
            .join(
                ContractVersion,
                ContractVersion.contract_id
                == Contract.contract_id,
            )
            .filter(
                Contract.status == "APPROVED",

                ContractVersion.version_no
                == Contract.current_version,

                ContractVersion.effective_from
                <= today,
            )
            .order_by(
                ContractVersion.effective_from.asc()
            )
            .limit(limit)
            .all()
        )
        
        
    # New method to find contracts to expire based on effective date    
    @staticmethod
    def find_contracts_to_expire(
        db,
        today: date,
        limit: int = 100,
    ):
        return (
            db.query(Contract)
            .join(
                ContractVersion,
                ContractVersion.contract_id
                == Contract.contract_id,
            )
            .filter(
                Contract.status == "ACTIVE",

                ContractVersion.version_no
                == Contract.current_version,

                ContractVersion.effective_to
                < today,
            )
            .order_by(
                ContractVersion.effective_to.asc()
            )
            .limit(limit)
            .all()
        )
    
    
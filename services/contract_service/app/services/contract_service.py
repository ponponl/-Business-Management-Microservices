from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_version import ContractVersion
from app.models.contract_audit import ContractAudit
from app.repositories.customer_repository import CustomerRepository
from app.schemas.contract import CreateContractRequest


class ContractService:

    @staticmethod
    def create_contract(
        db: Session,
        request: CreateContractRequest,
        actor_id: UUID,
    ) -> Contract:

        customer = CustomerRepository.get_by_id(
            db,
            request.customer_id,
        )

        if not customer:
            raise ValueError("CUSTOMER_NOT_FOUND")

        if customer.status != "ACTIVE":
            raise ValueError("CUSTOMER_INACTIVE")

        try:
            contract = Contract(
                customer_id=request.customer_id,
                current_version=1,
                status="DRAFT",
                row_version=1,
            )

            db.add(contract)
            db.flush()

            version = ContractVersion(
                contract_id=contract.contract_id,
                version_no=1,
                effective_from=request.effective_from,
                effective_to=request.effective_to,
                contract_value=request.contract_value,
                payment_terms=request.payment_terms,
                service_terms=request.service_terms,
                created_by=actor_id,
                change_reason="Initial version",
            )

            db.add(version)

            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=version.version_id,
                actor_id=actor_id,
                action="CREATE",
                status_before=None,
                status_after="DRAFT",
                note="Contract created",
            )

            db.add(audit)

            db.commit()
            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import SYSTEM_ACTOR_ID
from app.core.contract_number import generate_contract_number
from app.core.event_builder import build_contract_event
from app.core.idempotency import build_request_hash

from app.models.contract import Contract
from app.models.contract_audit import ContractAudit
from app.models.contract_version import ContractVersion
from app.models.idempotency_key import IdempotencyKey
from app.models.outbox_event import OutboxEvent

from app.repositories.contract_repository import ContractRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.idempotency_repository import (
    IdempotencyRepository,
)

from app.schemas.contract import (
    CreateContractRequest,
    UpdateContractRequest,
    RenewContractRequest,
    CancelContractRequest,
)

from app.services.state_machine import (
    ContractStateMachine,
    ContractStatus,
)


class ContractService:

    # =========================================================
    # CREATE CONTRACT
    # =========================================================
    @staticmethod
    def create_contract(
        db: Session,
        request: CreateContractRequest,
        actor_id: UUID,
    ) -> Contract:

        # 1. Validate customer
        customer = CustomerRepository.get_by_id(
            db,
            request.customer_id,
        )

        if customer is None:
            raise ValueError(
                "CUSTOMER_NOT_FOUND"
            )

        if customer.status != "ACTIVE":
            raise ValueError(
                "CUSTOMER_INACTIVE"
            )

        try:
            # 2. Generate business contract number
            contract_number = (
                generate_contract_number()
            )

            # 3. Create Contract
            contract = Contract(
                contract_number=contract_number,
                customer_id=request.customer_id,
                current_version=1,
                status=ContractStatus.DRAFT.value,
                row_version=1,
            )

            db.add(contract)

            # Generate contract_id
            db.flush()

            # 4. Create Version 1
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

            db.flush()

            # 5. Create Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=version.version_id,
                actor_id=actor_id,
                action="CREATE",
                status_before=None,
                status_after=contract.status,
                note="Contract created",
            )

            db.add(audit)

            # 6. Build event envelope
            event = build_contract_event(
                event_name="CONTRACT_CREATED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "effective_from":
                        version.effective_from.isoformat(),
                    "effective_to":
                        version.effective_to.isoformat(),
                },
            )

            # 7. Create Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_CREATED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 8. Commit everything in one transaction
            db.commit()

            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise

    # =========================================================
    # GET CONTRACT
    # =========================================================
    @staticmethod
    def get_contract(
        db: Session,
        contract_id: UUID,
    ) -> tuple[Contract, ContractVersion]:

        contract = ContractRepository.get_by_id(
            db,
            contract_id,
        )

        if contract is None:
            raise ValueError(
                "CONTRACT_NOT_FOUND"
            )

        version = (
            ContractRepository.get_current_version(
                db,
                contract,
            )
        )

        if version is None:
            raise ValueError(
                "CURRENT_VERSION_NOT_FOUND"
            )

        return contract, version

    # =========================================================
    # LIST CONTRACTS
    # =========================================================
    @staticmethod
    def list_contracts(
        db: Session,
        customer_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        contracts = (
            ContractRepository.list_contracts(
                db=db,
                customer_id=customer_id,
                status=status,
                skip=skip,
                limit=limit,
            )
        )

        total = (
            ContractRepository.count_contracts(
                db=db,
                customer_id=customer_id,
                status=status,
            )
        )

        return contracts, total

    # =========================================================
    # UPDATE CONTRACT
    # =========================================================
    @staticmethod
    def update_contract(
        db: Session,
        contract_id: UUID,
        request: UpdateContractRequest,
        actor_id: UUID,
    ) -> Contract:

        try:
            # 1. Lock Contract row
            contract = (
                ContractRepository.get_by_id_for_update(
                    db,
                    contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 2. Update chỉ được phép ở DRAFT
            # hoặc REVISION_REQUESTED
            if contract.status not in {
                ContractStatus.DRAFT.value,
                ContractStatus.REVISION_REQUESTED.value,
            }:
                raise ValueError(
                    "INVALID_STATE"
                )

            # 3. Optimistic locking
            if contract.row_version != request.row_version:
                raise ValueError(
                    "VERSION_CONFLICT"
                )

            # 4. Next contract version
            next_version_no = (
                contract.current_version + 1
            )

            # 5. Create new version
            new_version = ContractVersion(
                contract_id=contract.contract_id,
                version_no=next_version_no,
                effective_from=request.effective_from,
                effective_to=request.effective_to,
                contract_value=request.contract_value,
                payment_terms=request.payment_terms,
                service_terms=request.service_terms,
                created_by=actor_id,
                change_reason="Contract updated",
            )

            db.add(new_version)

            db.flush()

            # 6. Update Contract aggregate
            previous_status = contract.status

            contract.current_version = (
                next_version_no
            )

            contract.row_version += 1

            # 7. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=new_version.version_id,
                actor_id=actor_id,
                action="UPDATE",
                status_before=previous_status,
                status_after=contract.status,
                note="Contract content updated",
            )

            db.add(audit)

            # 8. Build event
            event = build_contract_event(
                event_name="CONTRACT_UPDATED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "effective_from":
                        new_version.effective_from.isoformat(),
                    "effective_to":
                        new_version.effective_to.isoformat(),
                },
            )

            # 9. Create Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_UPDATED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 10. Commit
            db.commit()

            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise

    # =========================================================
    # SUBMIT CONTRACT
    # =========================================================
    @staticmethod
    def submit_contract(
        db: Session,
        contract_id: UUID,
        idempotency_key: str,
        actor_id: UUID,
    ):
        operation = "SUBMIT_CONTRACT"

        request_hash = build_request_hash(
            operation=operation,
            resource_id=str(contract_id),
        )

        try:
            # 1. Check Idempotency
            existing = (
                IdempotencyRepository.get_by_key(
                    db,
                    idempotency_key,
                )
            )

            if existing is not None:

                if (
                    existing.operation != operation
                    or existing.resource_id != contract_id
                    or existing.request_hash != request_hash
                ):
                    raise ValueError(
                        "IDEMPOTENCY_KEY_REUSED"
                    )

                return (
                    existing.response_status,
                    existing.response_body,
                )

            # 2. Lock Contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db,
                    contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 3. Validate state
            if contract.status not in {
                ContractStatus.DRAFT.value,
                ContractStatus.REVISION_REQUESTED.value,
            }:
                raise ValueError(
                    "INVALID_STATE"
                )

            # 4. Validate Customer
            customer = (
                CustomerRepository.get_by_id(
                    db,
                    contract.customer_id,
                )
            )

            if customer is None:
                raise ValueError(
                    "CUSTOMER_NOT_FOUND"
                )

            if customer.status != "ACTIVE":
                raise ValueError(
                    "CUSTOMER_INACTIVE"
                )

            # 5. Validate current version
            version = (
                ContractRepository.get_current_version(
                    db,
                    contract,
                )
            )

            if version is None:
                raise ValueError(
                    "CURRENT_VERSION_NOT_FOUND"
                )

            # 6. State transition
            previous_status = contract.status

            new_status = (
                ContractStateMachine.transition(
                    ContractStatus(
                        contract.status
                    ),
                    "submit",
                )
            )

            contract.status = new_status.value

            # IMPORTANT:
            # Submit cũng là aggregate change
            contract.row_version += 1

            # 7. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=version.version_id,
                actor_id=actor_id,
                action="SUBMIT",
                status_before=previous_status,
                status_after=contract.status,
                note="Contract submitted",
            )

            db.add(audit)

            # 8. Build event
            event = build_contract_event(
                event_name="CONTRACT_SUBMITTED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "effective_from":
                        version.effective_from.isoformat(),
                    "effective_to":
                        version.effective_to.isoformat(),
                },
            )

            # 9. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_SUBMITTED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 10. Response
            response_body = {
                "contract_id":
                    str(contract.contract_id),
                "contract_number":
                    contract.contract_number,
                "status":
                    contract.status,
                "message":
                    "Contract submitted successfully",
            }

            # 11. Idempotency record
            IdempotencyRepository.create(
                db,
                key=idempotency_key,
                operation=operation,
                resource_id=contract.contract_id,
                request_hash=request_hash,
                response_status=202,
                response_body=response_body,
            )

            # 12. Commit
            db.commit()

            return 202, response_body

        except Exception:
            db.rollback()
            raise

    # =========================================================
    # RENEW CONTRACT
    # =========================================================
    @staticmethod
    def renew_contract(
        db: Session,
        contract_id: UUID,
        request: RenewContractRequest,
        actor_id: UUID,
    ) -> Contract:

        try:
            # 1. Lock contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db,
                    contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 2. Renew chỉ ACTIVE
            if contract.status != (
                ContractStatus.ACTIVE.value
            ):
                raise ValueError(
                    "RENEW_NOT_ALLOWED"
                )

            # 3. Current version
            current_version = (
                ContractRepository.get_current_version(
                    db,
                    contract,
                )
            )

            if current_version is None:
                raise ValueError(
                    "CURRENT_VERSION_NOT_FOUND"
                )

            # 4. New end date phải lớn hơn
            if (
                request.new_effective_to
                <= current_version.effective_to
            ):
                raise ValueError(
                    "INVALID_RENEWAL_DATE"
                )

            # 5. Create new version
            next_version_no = (
                contract.current_version + 1
            )

            new_version = ContractVersion(
                contract_id=contract.contract_id,
                version_no=next_version_no,
                effective_from=(
                    current_version.effective_from
                ),
                effective_to=(
                    request.new_effective_to
                ),
                contract_value=(
                    current_version.contract_value
                ),
                payment_terms=(
                    current_version.payment_terms
                ),
                service_terms=(
                    current_version.service_terms
                ),
                created_by=actor_id,
                change_reason=request.reason,
            )

            db.add(new_version)

            db.flush()

            # 6. Update Contract
            contract.current_version = (
                next_version_no
            )

            contract.row_version += 1

            # ACTIVE remains ACTIVE
            previous_status = contract.status

            # 7. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=new_version.version_id,
                actor_id=actor_id,
                action="RENEW",
                status_before=previous_status,
                status_after=contract.status,
                note=request.reason,
            )

            db.add(audit)

            # 8. Event
            event = build_contract_event(
                event_name="CONTRACT_RENEWED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "effective_from":
                        new_version.effective_from.isoformat(),
                    "effective_to":
                        new_version.effective_to.isoformat(),
                },
            )

            # 9. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_RENEWED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 10. Commit
            db.commit()

            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise

    # =========================================================
    # CANCEL CONTRACT
    # =========================================================
    @staticmethod
    def cancel_contract(
        db: Session,
        contract_id: UUID,
        request: CancelContractRequest,
        actor_id: UUID,
    ) -> Contract:

        try:
            # 1. Lock Contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db,
                    contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 2. Only 3 states can be cancelled
            if contract.status not in {
                ContractStatus.DRAFT.value,
                ContractStatus.SUBMITTED.value,
                ContractStatus.REVISION_REQUESTED.value,
            }:
                raise ValueError(
                    "CANCEL_NOT_ALLOWED"
                )

            # 3. Previous status
            previous_status = contract.status

            # 4. State transition
            new_status = (
                ContractStateMachine.transition(
                    ContractStatus(
                        contract.status
                    ),
                    "cancel",
                )
            )

            contract.status = new_status.value

            # 5. Aggregate version
            contract.row_version += 1

            # 6. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=None,
                actor_id=actor_id,
                action="CANCEL",
                status_before=previous_status,
                status_after=contract.status,
                note=request.reason,
            )

            db.add(audit)

            # 7. Event
            event = build_contract_event(
                event_name="CONTRACT_CANCELLED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "reason":
                        request.reason,
                },
            )

            # 8. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_CANCELLED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 9. Commit
            db.commit()

            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise

    # =========================================================
    # ACTIVATE CONTRACT
    # =========================================================
    @staticmethod
    def activate_contract(
        db: Session,
        contract_id: UUID,
    ) -> Contract:

        try:
            # 1. Lock Contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db,
                    contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 2. Only APPROVED can activate
            if contract.status != (
                ContractStatus.APPROVED.value
            ):
                raise ValueError(
                    "INVALID_STATE"
                )

            # 3. Current version
            version = (
                ContractRepository.get_current_version(
                    db,
                    contract,
                )
            )

            if version is None:
                raise ValueError(
                    "CURRENT_VERSION_NOT_FOUND"
                )

            # 4. Check effective date
            today = date.today()

            if today < version.effective_from:
                raise ValueError(
                    "NOT_YET_EFFECTIVE"
                )

            # 5. State transition
            previous_status = contract.status

            new_status = (
                ContractStateMachine.transition(
                    ContractStatus(
                        contract.status
                    ),
                    "activate",
                )
            )

            contract.status = new_status.value

            # 6. Aggregate version
            contract.row_version += 1

            # 7. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=version.version_id,
                actor_id=SYSTEM_ACTOR_ID,
                action="ACTIVATE",
                status_before=previous_status,
                status_after=contract.status,
                note="Contract activated automatically",
            )

            db.add(audit)

            # 8. Event
            event = build_contract_event(
                event_name="CONTRACT_ACTIVATED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "effective_from":
                        version.effective_from.isoformat(),
                    "effective_to":
                        version.effective_to.isoformat(),
                },
            )

            # 9. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_ACTIVATED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 10. Commit
            db.commit()

            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise

    # =========================================================
    # EXPIRE CONTRACT
    # =========================================================
    @staticmethod
    def expire_contract(
        db: Session,
        contract_id: UUID,
    ) -> Contract:

        try:
            # 1. Lock Contract
            contract = (
                ContractRepository.get_by_id_for_update(
                    db,
                    contract_id,
                )
            )

            if contract is None:
                raise ValueError(
                    "CONTRACT_NOT_FOUND"
                )

            # 2. Only ACTIVE can expire
            if contract.status != (
                ContractStatus.ACTIVE.value
            ):
                raise ValueError(
                    "INVALID_STATE"
                )

            # 3. Current version
            version = (
                ContractRepository.get_current_version(
                    db,
                    contract,
                )
            )

            if version is None:
                raise ValueError(
                    "CURRENT_VERSION_NOT_FOUND"
                )

            # 4. Check expiration date
            today = date.today()

            if today <= version.effective_to:
                raise ValueError(
                    "NOT_EXPIRED_YET"
                )

            # 5. State transition
            previous_status = contract.status

            new_status = (
                ContractStateMachine.transition(
                    ContractStatus(
                        contract.status
                    ),
                    "expire",
                )
            )

            contract.status = new_status.value

            # 6. Aggregate version
            contract.row_version += 1

            # 7. Audit
            audit = ContractAudit(
                contract_id=contract.contract_id,
                version_id=version.version_id,
                actor_id=SYSTEM_ACTOR_ID,
                action="EXPIRE",
                status_before=previous_status,
                status_after=contract.status,
                note="Contract expired automatically",
            )

            db.add(audit)

            # 8. Event
            event = build_contract_event(
                event_name="CONTRACT_EXPIRED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number":
                        contract.contract_number,
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version":
                        contract.current_version,
                    "status":
                        contract.status,
                    "effective_from":
                        version.effective_from.isoformat(),
                    "effective_to":
                        version.effective_to.isoformat(),
                },
            )

            # 9. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_EXPIRED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 10. Commit
            db.commit()

            db.refresh(contract)

            return contract

        except Exception:
            db.rollback()
            raise
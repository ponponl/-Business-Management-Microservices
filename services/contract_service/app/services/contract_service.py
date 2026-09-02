from datetime import date
import logging
from uuid import UUID
import uuid

from fastapi import UploadFile

from app.models.contract_attachment import ContractAttachment
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

from app.services.attachment_validator import (
    read_and_validate_file,
)
from app.utils.attachment import (
    build_attachment_object_key,
)
from app.services.file_storage import storage



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

logger = logging.getLogger(__name__)


class ContractService:
    
    
    @staticmethod
    def build_contract_response(
        contract: Contract,
        version: ContractVersion,
        attachments: list[ContractAttachment] | None = None,
    ):
        return {
            "contract_id": contract.contract_id,
            "contract_number": contract.contract_number,
            "customer_id": contract.customer_id,
            "current_version": contract.current_version,
            "status": contract.status,
            "row_version": contract.row_version,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
            "current_version_detail": version,
            "attachments": attachments or [],
        }
    # =========================================================
    # CREATE CONTRACT
    # =========================================================
    # =========================================================

    @staticmethod
    async def create_contract(
        db: Session,
        request: CreateContractRequest,
        actor_id: UUID,
        attachments: list[UploadFile] | None = None,
    ) -> dict:

        # -----------------------------------------------------
        # 1. Validate customer
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # 2. Track physical files
        # -----------------------------------------------------

        saved_object_keys: list[str] = []

        try:

            # -------------------------------------------------
            # 3. Generate contract number
            # -------------------------------------------------

            contract_number = (
                generate_contract_number()
            )

            # -------------------------------------------------
            # 4. Create Contract
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 5. Create Version 1
            # -------------------------------------------------

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

            # Generate version_id
            db.flush()

            # -------------------------------------------------
            # 6. Validate duplicate attachment names
            # -------------------------------------------------

            normalized_attachments = (
                attachments or []
            )

            file_names: set[str] = set()

            for file in normalized_attachments:

                if not file.filename:
                    raise ValueError(
                        "INVALID_FILE_NAME"
                    )

                safe_file_name = (
                    file.filename
                    .replace("\\", "/")
                    .split("/")[-1]
                )

                if safe_file_name in file_names:
                    raise ValueError(
                        "DUPLICATE_FILE_NAME"
                    )

                file_names.add(
                    safe_file_name
                )

            # -------------------------------------------------
            # 7. Upload Attachments
            # -------------------------------------------------

            created_attachments = []

            for file in normalized_attachments:

                content = (
                    await read_and_validate_file(
                        file
                    )
                )

                attachment_id = uuid.uuid4()

                object_key = (
                    build_attachment_object_key(
                        contract.contract_id,
                        version.version_id,
                        attachment_id,
                    )
                )

                # Physical file
                storage.save(
                    content,
                    object_key,
                )

                saved_object_keys.append(
                    object_key
                )

                safe_file_name = (
                    file.filename
                    .replace("\\", "/")
                    .split("/")[-1]
                )

                attachment = ContractAttachment(
                    attachment_id=attachment_id,
                    version_id=version.version_id,
                    file_name=safe_file_name,
                    object_key=object_key,
                    content_type=file.content_type,
                    file_size=len(content),
                    uploaded_by=actor_id,
                )

                db.add(attachment)

                created_attachments.append(
                    attachment
                )

            if created_attachments:
                db.flush()

            # -------------------------------------------------
            # 8. Audit
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 9. Event
            # -------------------------------------------------

            event = build_contract_event(
                event_name="CONTRACT_CREATED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number": (
                        contract.contract_number
                    ),
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version": (
                        contract.current_version
                    ),
                    "status": contract.status,
                    "effective_from": (
                        version.effective_from.isoformat()
                    ),
                    "effective_to": (
                        version.effective_to.isoformat()
                    ),
                },
            )

            # -------------------------------------------------
            # 10. Outbox
            # -------------------------------------------------

            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_CREATED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # -------------------------------------------------
            # 11. Commit
            # -------------------------------------------------

            db.commit()

            db.refresh(contract)

            return ContractService.build_contract_response(
                contract=contract,
                version=version,
                attachments=created_attachments,
            )

        except Exception:

            db.rollback()

            # ---------------------------------------------
            # Cleanup physical files if DB transaction fails
            # ---------------------------------------------

            for object_key in saved_object_keys:

                try:
                    storage.delete(
                        object_key
                    )

                except Exception:

                    logger.exception(
                        "Failed to cleanup attachment %s",
                        object_key,
                    )

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
            ContractRepository
            .get_current_version_with_attachments(
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

        serialized = []
        for contract in contracts:
            version = ContractRepository.get_current_version(
                db,
                contract,
            )

            serialized.append({
                "contract_id": contract.contract_id,
                "contract_number": contract.contract_number,
                "customer_id": contract.customer_id,
                "current_version": contract.current_version,
                "status": contract.status,
                "row_version": contract.row_version,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "effective_from": version.effective_from if version else None,
                "effective_to": version.effective_to if version else None,
                "contract_value": version.contract_value if version else None,
            })

        return serialized, total

    # =========================================================
    # UPDATE CONTRACT
    # =========================================================
    @staticmethod
    async def update_contract(
        db: Session,
        contract_id: UUID,
        request: UpdateContractRequest,
        actor_id: UUID,
        attachments: list[UploadFile] | None = None,
    ) -> dict:

        saved_object_keys: list[str] = []

        try:

            # -------------------------------------------------
            # 1. Lock Contract row
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 2. Validate state
            # -------------------------------------------------

            if contract.status not in {
                ContractStatus.DRAFT.value,
                ContractStatus.REVISION_REQUESTED.value,
            }:
                raise ValueError(
                    "INVALID_STATE"
                )

            # -------------------------------------------------
            # 3. Optimistic locking
            # -------------------------------------------------

            if (
                contract.row_version
                != request.row_version
            ):
                raise ValueError(
                    "VERSION_CONFLICT"
                )

            # -------------------------------------------------
            # 4. New version
            # -------------------------------------------------

            next_version_no = (
                contract.current_version + 1
            )

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

            # -------------------------------------------------
            # 5. Update aggregate
            # -------------------------------------------------

            previous_status = contract.status

            contract.current_version = (
                next_version_no
            )

            contract.row_version += 1

            # -------------------------------------------------
            # 6. Validate duplicate attachment names
            # -------------------------------------------------

            normalized_attachments = (
                attachments or []
            )

            file_names: set[str] = set()

            for file in normalized_attachments:

                if not file.filename:
                    raise ValueError(
                        "INVALID_FILE_NAME"
                    )

                safe_file_name = (
                    file.filename
                    .replace("\\", "/")
                    .split("/")[-1]
                )

                if safe_file_name in file_names:

                    raise ValueError(
                        "DUPLICATE_FILE_NAME"
                    )

                file_names.add(
                    safe_file_name
                )

            # -------------------------------------------------
            # 7. Upload attachments to NEW VERSION
            # -------------------------------------------------

            created_attachments = []

            for file in normalized_attachments:

                content = (
                    await read_and_validate_file(
                        file
                    )
                )

                attachment_id = uuid.uuid4()

                object_key = (
                    build_attachment_object_key(
                        contract.contract_id,
                        new_version.version_id,
                        attachment_id,
                    )
                )

                storage.save(
                    content,
                    object_key,
                )

                saved_object_keys.append(
                    object_key
                )

                safe_file_name = (
                    file.filename
                    .replace("\\", "/")
                    .split("/")[-1]
                )

                attachment = ContractAttachment(
                    attachment_id=attachment_id,
                    version_id=new_version.version_id,
                    file_name=safe_file_name,
                    object_key=object_key,
                    content_type=file.content_type,
                    file_size=len(content),
                    uploaded_by=actor_id,
                )

                db.add(attachment)

                created_attachments.append(
                    attachment
                )

            if created_attachments:
                db.flush()

            # -------------------------------------------------
            # 8. Audit
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 9. Event
            # -------------------------------------------------

            event = build_contract_event(
                event_name="CONTRACT_UPDATED",
                contract_id=contract.contract_id,
                payload={
                    "contract_id": str(
                        contract.contract_id
                    ),
                    "contract_number": (
                        contract.contract_number
                    ),
                    "customer_id": str(
                        contract.customer_id
                    ),
                    "current_version": (
                        contract.current_version
                    ),
                    "status": contract.status,
                    "effective_from": (
                        new_version
                        .effective_from
                        .isoformat()
                    ),
                    "effective_to": (
                        new_version
                        .effective_to
                        .isoformat()
                    ),
                },
            )

            # -------------------------------------------------
            # 10. Outbox
            # -------------------------------------------------

            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_UPDATED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # -------------------------------------------------
            # 11. Commit
            # -------------------------------------------------

            db.commit()

            db.refresh(contract)

            return ContractService.build_contract_response(
                contract=contract,
                version=new_version,
                attachments=created_attachments,
            )

        except Exception:

            db.rollback()

            for object_key in saved_object_keys:

                try:
                    storage.delete(
                        object_key
                    )

                except Exception:

                    logger.exception(
                        "Failed to cleanup attachment %s",
                        object_key,
                    )

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

            # 6. Validate effective period
            if version.effective_from > version.effective_to:
                raise ValueError(
                    "INVALID_EFFECTIVE_PERIOD"
                )

            # 7. Validate attachment requirement
            if not version.attachments:
                raise ValueError(
                    "ATTACHMENT_REQUIRED"
                )

            # 8. State transition
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

            # Submit is an aggregate change
            contract.row_version += 1

            # 9. Audit
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

            # 10. Build event
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

            # 11. Outbox
            outbox_event = OutboxEvent(
                aggregate_type="CONTRACT",
                aggregate_id=contract.contract_id,
                event_type="CONTRACT_SUBMITTED",
                payload=event,
                status="PENDING",
                retry_count=0,
            )

            db.add(outbox_event)

            # 12. Response
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

            # 13. Idempotency record
            IdempotencyRepository.create(
                db,
                key=idempotency_key,
                operation=operation,
                resource_id=contract.contract_id,
                request_hash=request_hash,
                response_status=202,
                response_body=response_body,
            )

            # 14. Commit
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
        
    # Validate contract for payment
    @staticmethod
    def validate_for_payment(
        db: Session,
        contract_id: UUID,
        customer_id: UUID,
        billing_period_start: date,
        billing_period_end: date,
    ):
        """
        Validate whether a contract is eligible
        for creating a payment board.

        This method is READ-ONLY.
        It does not modify Contract state,
        create Audit, Version, or Outbox events.
        """

        # =====================================================
        # 1. Validate billing period
        # =====================================================

        if billing_period_end < billing_period_start:
            return {
                "valid": False,
                "reason_code": "INVALID_BILLING_PERIOD",
                "message": (
                    "Kỳ thanh toán kết thúc "
                    "không được trước ngày bắt đầu."
                ),
            }

        # =====================================================
        # 2. Find Contract
        # =====================================================

        contract = ContractRepository.get_by_id(
            db,
            contract_id,
        )

        if contract is None:
            return {
                "valid": False,
                "reason_code": "CONTRACT_NOT_FOUND",
                "message": "Không tìm thấy hợp đồng.",
            }

        # =====================================================
        # 3. Validate customer
        # =====================================================

        if contract.customer_id != customer_id:
            return {
                "valid": False,
                "reason_code": "CUSTOMER_CONTRACT_MISMATCH",
                "message": (
                    "Khách hàng không thuộc hợp đồng."
                ),
            }

        # =====================================================
        # 4. Contract must be ACTIVE
        # =====================================================

        if contract.status != ContractStatus.ACTIVE.value:
            return {
                "valid": False,
                "reason_code": "CONTRACT_NOT_ACTIVE",
                "message": (
                    "Hợp đồng không ở trạng thái ACTIVE."
                ),
            }

        # =====================================================
        # 5. Get current contract version
        # =====================================================

        current_version = (
            ContractRepository.get_current_version(
                db,
                contract,
            )
        )

        if current_version is None:
            return {
                "valid": False,
                "reason_code": "CURRENT_VERSION_NOT_FOUND",
                "message": (
                    "Không tìm thấy phiên bản hiện hành "
                    "của hợp đồng."
                ),
            }

        # =====================================================
        # 6. Validate billing period against
        #    contract validity period
        # =====================================================

        if (
            billing_period_start
            < current_version.effective_from
            or
            billing_period_end
            > current_version.effective_to
        ):
            return {
                "valid": False,
                "reason_code": "BILLING_PERIOD_OUT_OF_RANGE",
                "message": (
                    "Kỳ thanh toán nằm ngoài "
                    "thời gian hiệu lực của hợp đồng."
                ),
            }

        # =====================================================
        # 7. Valid
        # =====================================================

        return {
            "valid": True,
            "contract_id": contract.contract_id,
            "contract_number": (
                contract.contract_number
            ),
            "customer_id": contract.customer_id,
            "status": contract.status,
            "current_version": (
                contract.current_version
            ),
            "effective_from": (
                current_version.effective_from
            ),
            "effective_to": (
                current_version.effective_to
            ),
            "reason_code": None,
            "message": (
                "Hợp đồng hợp lệ cho kỳ thanh toán."
            ),
        }
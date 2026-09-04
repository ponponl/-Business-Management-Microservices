from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, func

from app.models.contract import Contract
from app.models.contract_audit import ContractAudit
from app.models.contract_approval import ContractApproval
from app.models.customer import Customer
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
    def get_current_version_with_attachments(
        db: Session,
        contract: Contract,
    ) -> ContractVersion | None:

        return (
            db.query(ContractVersion)
            .options(
                selectinload(
                    ContractVersion.attachments
                )
            )
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
        search: str | None = None,
        effective_date: date | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Contract]:

        query = (
            db.query(Contract)
            .options(
                selectinload(Contract.versions),
                selectinload(Contract.audits),
                selectinload(Contract.approval_records),
            )
        )

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

        if search:
            query = query.filter(
                (Contract.contract_number.ilike(f"%{search}%")
                 | Contract.customer.has(Customer.company_name.ilike(f"%{search}%")))
            )

        if effective_date is not None:
            query = query.join(ContractVersion).filter(
                ContractVersion.version_no == Contract.current_version,
                ContractVersion.effective_from <= effective_date,
                ContractVersion.effective_to >= effective_date,
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
        search: str | None = None,
        effective_date: date | None = None,
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

        if search:
            query = query.filter(
                (Contract.contract_number.ilike(f"%{search}%")
                 | Contract.customer.has(Customer.company_name.ilike(f"%{search}%")))
            )

        if effective_date is not None:
            query = query.join(ContractVersion).filter(
                ContractVersion.version_no == Contract.current_version,
                ContractVersion.effective_from <= effective_date,
                ContractVersion.effective_to >= effective_date,
            )

        return query.count()

    # =========================================================
    # LIFECYCLE
    # =========================================================

    @staticmethod
    def find_contracts_to_activate(
        db: Session,
        today: date,
        limit: int = 100,
        exclude_contract_ids: set[UUID] | None = None,
    ):

        query = (
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
        )

        if exclude_contract_ids:
            query = query.filter(
                ~Contract.contract_id.in_(exclude_contract_ids)
            )

        return query.limit(limit).all()

    @staticmethod
    def find_contracts_to_expire(
        db: Session,
        today: date,
        limit: int = 100,
        exclude_contract_ids: set[UUID] | None = None,
    ):

        query = (
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
        )

        if exclude_contract_ids:
            query = query.filter(
                ~Contract.contract_id.in_(exclude_contract_ids)
            )

        return query.limit(limit).all()

    @staticmethod
    def contract_summary(db: Session) -> dict[str, int]:
        counts = dict(
            db.query(Contract.status, func.count(Contract.contract_id))
            .group_by(Contract.status)
            .all()
        )

        latest_revision = (
            db.query(
                ContractAudit.contract_id,
                func.max(ContractVersion.version_no).label("latest_version_no"),
            )
            .join(
                ContractVersion,
                ContractVersion.version_id == ContractAudit.version_id,
            )
            .filter(
                ContractAudit.action.in_(
                    {"MANAGER_REQUEST_REVISION", "DIRECTOR_REQUEST_REVISION"}
                )
            )
            .group_by(ContractAudit.contract_id)
            .subquery()
        )
        revision_roles = dict(
            db.query(ContractAudit.action, func.count(ContractAudit.contract_id))
            .join(
                ContractVersion,
                ContractVersion.version_id == ContractAudit.version_id,
            )
            .join(
                latest_revision,
                and_(
                    ContractAudit.contract_id == latest_revision.c.contract_id,
                    ContractVersion.version_no == latest_revision.c.latest_version_no,
                ),
            )
            .join(Contract, Contract.contract_id == ContractAudit.contract_id)
            .filter(Contract.status == "REVISION_REQUESTED")
            .group_by(ContractAudit.action)
            .all()
        )
        revision_roles = dict(revision_roles)

        latest_approval_round = (
            db.query(
                ContractApproval.contract_id,
                func.max(ContractApproval.approval_round).label("approval_round"),
            )
            .group_by(ContractApproval.contract_id)
            .subquery()
        )
        director_revision_count = (
            db.query(func.count(ContractApproval.approval_id))
            .join(
                latest_approval_round,
                and_(
                    ContractApproval.contract_id
                    == latest_approval_round.c.contract_id,
                    ContractApproval.approval_round
                    == latest_approval_round.c.approval_round,
                ),
            )
            .filter(
                ContractApproval.step_no == 2,
                ContractApproval.status == "REVISION_REQUESTED",
            )
            .scalar()
            or 0
        )

        return {
            "total": sum(counts.values()),
            "draft": counts.get("DRAFT", 0),
            "submitted": counts.get("SUBMITTED", 0),
            "manager_review": counts.get("MANAGER_REVIEW", 0),
            "director_review": counts.get("DIRECTOR_REVIEW", 0),
            "approved": counts.get("APPROVED", 0),
            "active": counts.get("ACTIVE", 0),
            "revision_requested": counts.get("REVISION_REQUESTED", 0),
            "revision_requested_by_manager": revision_roles.get("MANAGER_REQUEST_REVISION", 0),
            "revision_requested_by_director": director_revision_count,
            "rejected": counts.get("REJECTED", 0),
            "expired": counts.get("EXPIRED", 0),
            "cancelled": counts.get("CANCELLED", 0),
        }

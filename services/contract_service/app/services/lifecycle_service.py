import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.contract_clock import contract_today
from app.db.session import engine
from app.repositories.contract_repository import (
    ContractRepository,
)
from app.services.contract_service import (
    ContractService,
)


logger = logging.getLogger(__name__)


class ContractLifecycleService:

    DEFAULT_BATCH_SIZE = 100
    # A stable, service-specific PostgreSQL advisory-lock key. Session-level
    # locking is intentional: lifecycle actions commit once per contract, so a
    # transaction-level lock would be released after the first activation.
    ADVISORY_LOCK_ID = 43001001

    @staticmethod
    def process_activations(
        db,
        today: date,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> int:

        success_count = 0
        failed_contract_ids = set()

        while True:
            contracts = ContractRepository.find_contracts_to_activate(
                db=db,
                today=today,
                limit=batch_size,
                exclude_contract_ids=failed_contract_ids,
            )

            if not contracts:
                break

            for contract in contracts:
                contract_id = contract.contract_id
                contract_number = contract.contract_number

                try:
                    ContractService.activate_contract(
                        db=db,
                        contract_id=contract_id,
                    )
                    success_count += 1

                    logger.info(
                        "Contract activated: contract_id=%s "
                        "contract_number=%s",
                        contract_id,
                        contract_number,
                    )

                except ValueError as exc:
                    db.rollback()
                    failed_contract_ids.add(contract_id)

                    logger.warning(
                        "Failed to activate contract: "
                        "contract_id=%s error=%s",
                        contract_id,
                        exc,
                    )

                except Exception:
                    db.rollback()
                    failed_contract_ids.add(contract_id)

                    logger.exception(
                        "Unexpected error activating contract_id=%s",
                        contract_id,
                    )

        return success_count

    @staticmethod
    def process_expirations(
        db,
        today: date,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> int:

        success_count = 0
        failed_contract_ids = set()

        while True:
            contracts = ContractRepository.find_contracts_to_expire(
                db=db,
                today=today,
                limit=batch_size,
                exclude_contract_ids=failed_contract_ids,
            )

            if not contracts:
                break

            for contract in contracts:
                contract_id = contract.contract_id
                contract_number = contract.contract_number

                try:
                    ContractService.expire_contract(
                        db=db,
                        contract_id=contract_id,
                    )
                    success_count += 1

                    logger.info(
                        "Contract expired: contract_id=%s "
                        "contract_number=%s",
                        contract_id,
                        contract_number,
                    )

                except ValueError as exc:
                    db.rollback()
                    failed_contract_ids.add(contract_id)

                    logger.warning(
                        "Failed to expire contract: "
                        "contract_id=%s error=%s",
                        contract_id,
                        exc,
                    )

                except Exception:
                    db.rollback()
                    failed_contract_ids.add(contract_id)

                    logger.exception(
                        "Unexpected error expiring contract_id=%s",
                        contract_id,
                    )

        return success_count

    @staticmethod
    def run_once(
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> dict[str, int | bool]:
        # Pin the Session to one physical connection. Session-level advisory
        # locks belong to a PostgreSQL connection, while the lifecycle service
        # commits once per contract. Without pinning, a commit can return the
        # locked connection to the pool and the later unlock may run elsewhere.
        connection = engine.connect()
        db = Session(bind=connection)
        lock_acquired = False

        try:
            lock_acquired = bool(
                db.execute(
                    text(
                        "SELECT pg_try_advisory_lock(:lock_id)"
                    ),
                    {"lock_id": ContractLifecycleService.ADVISORY_LOCK_ID},
                ).scalar()
            )

            if not lock_acquired:
                logger.info(
                    "Contract lifecycle skipped: another process "
                    "holds the advisory lock"
                )
                return {
                    "activated": 0,
                    "expired": 0,
                    "skipped": True,
                }

            today = contract_today()

            activated_count = (
                ContractLifecycleService.process_activations(
                    db=db,
                    today=today,
                    batch_size=batch_size,
                )
            )

            expired_count = (
                ContractLifecycleService.process_expirations(
                    db=db,
                    today=today,
                    batch_size=batch_size,
                )
            )

            logger.info(
                "Contract lifecycle completed: "
                "date=%s activated=%d expired=%d",
                today,
                activated_count,
                expired_count,
            )

            return {
                "activated": activated_count,
                "expired": expired_count,
                "skipped": False,
            }

        except Exception:

            db.rollback()

            logger.exception(
                "Contract lifecycle worker failed"
            )

            return {
                "activated": 0,
                "expired": 0,
                "skipped": False,
            }

        finally:
            if lock_acquired:
                try:
                    db.rollback()
                    db.execute(
                        text(
                            "SELECT pg_advisory_unlock(:lock_id)"
                        ),
                        {
                            "lock_id": (
                                ContractLifecycleService.ADVISORY_LOCK_ID
                            )
                        },
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    logger.exception(
                        "Failed to release contract lifecycle "
                        "advisory lock"
                    )
            db.close()
            connection.close()

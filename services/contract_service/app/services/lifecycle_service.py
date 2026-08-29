from datetime import date

import logging

from app.db.session import SessionLocal
from app.repositories.contract_repository import (
    ContractRepository,
)
from app.services.contract_service import (
    ContractService,
)


logger = logging.getLogger(__name__)


class ContractLifecycleService:

    DEFAULT_BATCH_SIZE = 100

    @staticmethod
    def process_activations(
        db,
        today: date,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> int:

        contracts = (
            ContractRepository.find_contracts_to_activate(
                db=db,
                today=today,
                limit=batch_size,
            )
        )

        success_count = 0

        for contract in contracts:

            try:

                ContractService.activate_contract(
                    db=db,
                    contract_id=contract.contract_id,
                )

                success_count += 1

                logger.info(
                    "Contract activated: "
                    "contract_id=%s "
                    "contract_number=%s",
                    contract.contract_id,
                    contract.contract_number,
                )

            except ValueError as exc:

                db.rollback()

                logger.warning(
                    "Failed to activate contract: "
                    "contract_id=%s error=%s",
                    contract.contract_id,
                    exc,
                )

            except Exception:

                db.rollback()

                logger.exception(
                    "Unexpected error activating "
                    "contract_id=%s",
                    contract.contract_id,
                )

        return success_count

    @staticmethod
    def process_expirations(
        db,
        today: date,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> int:

        contracts = (
            ContractRepository.find_contracts_to_expire(
                db=db,
                today=today,
                limit=batch_size,
            )
        )

        success_count = 0

        for contract in contracts:

            try:

                ContractService.expire_contract(
                    db=db,
                    contract_id=contract.contract_id,
                )

                success_count += 1

                logger.info(
                    "Contract expired: "
                    "contract_id=%s "
                    "contract_number=%s",
                    contract.contract_id,
                    contract.contract_number,
                )

            except ValueError as exc:

                db.rollback()

                logger.warning(
                    "Failed to expire contract: "
                    "contract_id=%s error=%s",
                    contract.contract_id,
                    exc,
                )

            except Exception:

                db.rollback()

                logger.exception(
                    "Unexpected error expiring "
                    "contract_id=%s",
                    contract.contract_id,
                )

        return success_count

    @staticmethod
    def run_once(
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:

        today = date.today()

        db = SessionLocal()

        try:

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

        except Exception:

            db.rollback()

            logger.exception(
                "Contract lifecycle worker failed"
            )

        finally:
            db.close()
import logging

from apscheduler.schedulers.background import (
    BackgroundScheduler,
)

from app.services.lifecycle_service import (
    ContractLifecycleService,
)
from app.core.config import settings


logger = logging.getLogger(__name__)


scheduler = BackgroundScheduler(
    timezone=settings.CONTRACT_TIMEZONE,
)


def run_contract_lifecycle():
    try:

        ContractLifecycleService.run_once()

    except Exception:

        logger.exception(
            "Contract lifecycle scheduler job failed"
        )


def start_scheduler():

    if scheduler.running:
        return

    # Chạy một lần ngay khi service startup
    run_contract_lifecycle()

    scheduler.add_job(
        run_contract_lifecycle,
        trigger="interval",
        seconds=settings.CONTRACT_LIFECYCLE_INTERVAL_SECONDS,
        id="contract-lifecycle",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=max(
            30,
            settings.CONTRACT_LIFECYCLE_INTERVAL_SECONDS * 2,
        ),
    )

    scheduler.start()

    logger.info(
        "Contract lifecycle scheduler started"
    )


def stop_scheduler():

    if not scheduler.running:
        return

    scheduler.shutdown(wait=False)

    logger.info(
        "Contract lifecycle scheduler stopped"
    )

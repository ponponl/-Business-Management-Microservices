from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def contract_today() -> date:
    """Return the business date used by the Contract lifecycle."""

    return datetime.now(
        ZoneInfo(settings.CONTRACT_TIMEZONE)
    ).date()

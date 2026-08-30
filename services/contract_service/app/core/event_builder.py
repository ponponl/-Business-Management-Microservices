from datetime import datetime, timezone
from uuid import UUID, uuid4


def build_contract_event(
    *,
    event_name: str,
    contract_id: UUID,
    payload: dict,
) -> dict:

    return {
        "event_id": str(uuid4()),
        "event_name": event_name,
        "occurred_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "aggregate_type": "CONTRACT",
        "aggregate_id": str(contract_id),
        "version": 1,
        "payload": payload,
    }
import hashlib
import json


def build_request_hash(
    *,
    operation: str,
    resource_id: str,
) -> str:

    data = {
        "operation": operation,
        "resource_id": resource_id,
    }

    serialized = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()
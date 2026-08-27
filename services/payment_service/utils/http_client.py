import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException


def call_json(method: str, url: str, payload: dict | None = None, query: dict | None = None, authorization: str | None = None):
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise HTTPException(502, f"Upstream API trả HTTP {error.code}: {detail}") from error
    except (URLError, TimeoutError) as error:
        raise HTTPException(503, f"Không thể kết nối upstream API: {url}") from error

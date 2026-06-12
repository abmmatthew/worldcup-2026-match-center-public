from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://api.balldontlie.io/fifa/worldcup/v1"


@dataclass
class ApiResult:
    ok: bool
    status_code: Optional[int]
    endpoint: str
    url: str
    data: Any = None
    error: str = ""
    meta: Dict[str, Any] | None = None


def bdl_get(endpoint: str, api_key: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> ApiResult:
    """Call the BALLDONTLIE FIFA World Cup API using Authorization header auth."""
    if not api_key:
        return ApiResult(False, None, endpoint, "", error="Missing BALLDONTLIE API key.")

    endpoint = endpoint.strip().lstrip("/")
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Authorization": api_key.strip()}
    params = params or {}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        final_url = response.url
        try:
            payload = response.json()
        except Exception:
            payload = {"raw_text": response.text[:2000]}

        if response.status_code == 200:
            return ApiResult(True, response.status_code, endpoint, final_url, data=payload.get("data", payload), meta=payload.get("meta"))

        return ApiResult(
            False,
            response.status_code,
            endpoint,
            final_url,
            data=payload,
            error=_friendly_error(response.status_code, payload),
            meta=payload.get("meta") if isinstance(payload, dict) else None,
        )
    except Exception as exc:
        return ApiResult(False, None, endpoint, url, error=str(exc))


def bdl_get_all(endpoint: str, api_key: str, params: Optional[Dict[str, Any]] = None, max_pages: int = 5) -> ApiResult:
    """Fetch cursor-paginated BDL data. Stops after max_pages to avoid runaway calls."""
    params = dict(params or {})
    params.setdefault("per_page", 100)

    all_rows: List[Dict[str, Any]] = []
    last_result: ApiResult | None = None
    cursor = params.get("cursor")

    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor
        result = bdl_get(endpoint, api_key, params=params)
        last_result = result
        if not result.ok:
            return result

        rows = result.data or []
        if isinstance(rows, list):
            all_rows.extend(rows)
        else:
            return result

        meta = result.meta or {}
        cursor = meta.get("next_cursor")
        if not cursor:
            break

    if last_result is None:
        return ApiResult(False, None, endpoint, "", error="No API call was made.")

    return ApiResult(True, last_result.status_code, endpoint, last_result.url, data=all_rows, meta=last_result.meta)


def _friendly_error(status_code: int, payload: Any) -> str:
    detail = ""
    if isinstance(payload, dict):
        detail = payload.get("error") or payload.get("message") or payload.get("detail") or ""
    if status_code == 401:
        return "401 Unauthorized: missing API key, invalid key, or your account tier does not include this endpoint."
    if status_code == 400:
        return f"400 Bad Request: check endpoint parameters. {detail}".strip()
    if status_code == 404:
        return "404 Not Found: endpoint or resource ID was not found."
    if status_code == 406:
        return "406 Not Acceptable: requested response format is not JSON."
    if status_code == 429:
        return "429 Rate limit: too many requests. Wait and try again."
    if status_code == 500:
        return "500 Server Error from BALLDONTLIE. Try again later."
    if status_code == 503:
        return "503 Service unavailable from BALLDONTLIE. Try again later."
    return f"HTTP {status_code}: {detail}".strip()

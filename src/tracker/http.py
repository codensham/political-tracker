"""HTTP helpers with a bounded retry policy for rate limits and server errors."""

from __future__ import annotations

import re
import time
from collections.abc import Callable

import httpx

MAX_RETRIES = 3
BASE_DELAY = 1.0


def _retryable(status: int) -> bool:
    return status == 429 or status >= 500


_KEY_PARAM = re.compile(r"(api_key=)[^&\s'\")]+")


def redact(text: str) -> str:
    """Replace any api_key value in a string with REDACTED."""
    return _KEY_PARAM.sub(r"\1REDACTED", text)


def _get(
    client: httpx.Client,
    url: str,
    params: dict | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    for attempt in range(MAX_RETRIES + 1):
        resp = client.get(url, params=params)
        if _retryable(resp.status_code) and attempt < MAX_RETRIES:
            sleep(BASE_DELAY * 2**attempt)
            continue
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # The message embeds the full URL, which can carry api_key. Strip it before it
            # reaches logs, CI output or tracebacks.
            raise httpx.HTTPStatusError(
                redact(str(exc)), request=exc.request, response=exc.response
            ) from None
        return resp
    raise AssertionError("unreachable")


def get_json(
    client: httpx.Client,
    url: str,
    params: dict | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    return _get(client, url, params, sleep=sleep).json()


def get_bytes(
    client: httpx.Client,
    url: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    return _get(client, url, sleep=sleep).content

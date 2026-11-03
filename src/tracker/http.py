"""HTTP helpers with a bounded retry policy for rate limits and server errors."""

from __future__ import annotations

import time
from typing import Callable

import httpx

MAX_RETRIES = 3
BASE_DELAY = 1.0


def _retryable(status: int) -> bool:
    return status == 429 or status >= 500


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
        resp.raise_for_status()
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

"""Wayback Machine Save Page Now, anonymous and rate-limited (D-025).

A failed archive returns None. The article record stays valid with archive_url null.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

SAVE_URL = "https://web.archive.org/save/"
MAX_RETRIES = 2


def archive_url_for(
    client: httpx.Client,
    url: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Ask the Wayback Machine to save url. Return the snapshot URL, or None on failure."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.get(SAVE_URL + url, follow_redirects=True, timeout=60)
        except httpx.HTTPError:
            resp = None
        if resp is not None and resp.status_code == 200 and "/web/" in str(resp.url):
            return str(resp.url)
        retryable = resp is None or resp.status_code == 429 or resp.status_code >= 500
        if not retryable or attempt == MAX_RETRIES:
            return None
        sleep(5.0 * 2**attempt)
    return None

"""Official-position snapshots: hash a fetched platform page, flag change, store key quotes only.

The page text is used transiently and never written (spec §5, content rules).
"""

from __future__ import annotations

import hashlib

from tracker.checks import normalize


class KeyQuoteNotFound(ValueError):
    pass


def content_hash(page_text: str) -> str:
    """SHA-256 of the normalized page text, so whitespace and markup changes alone do not count."""
    return hashlib.sha256(normalize(page_text).encode("utf-8")).hexdigest()


def build_position(
    candidate_id: str,
    url: str,
    page_text: str,
    capture_date: str,
    *,
    previous_hash: str | None = None,
    key_quotes: list[str] | None = None,
    archive_url: str | None = None,
) -> dict:
    """Return a position record. Each key quote must appear verbatim in the page (D-024 spirit)."""
    quotes = list(key_quotes or [])
    normalized = normalize(page_text)
    for q in quotes:
        if normalize(q) not in normalized:
            raise KeyQuoteNotFound(f"key quote not found verbatim on {url}: {q[:60]!r}")
    digest = content_hash(page_text)
    return {
        "id": f"position-{candidate_id}-{capture_date}-{digest[:8]}",
        "type": "position",
        "candidate_ids": [candidate_id],
        "source_url": url,
        "published_at": capture_date,
        "topics": [],
        "url": url,
        "capture_date": capture_date,
        "archive_url": archive_url,
        "content_sha256": digest,
        "changed": previous_hash is not None and previous_hash != digest,
        "key_quotes": quotes,
    }

"""Match a candidate by full name or configured alias only (D-009). A bare surname never matches."""

from __future__ import annotations

import re


def _pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z])" + re.escape(phrase) + r"(?![A-Za-z])", re.IGNORECASE)


def matched_candidate_ids(text: str, candidates: list[dict]) -> list[str]:
    """Return candidate ids whose name or any alias appears in text as a whole phrase."""
    found = []
    for cand in candidates:
        phrases = [cand["name"], *cand.get("aliases", [])]
        if any(_pattern(p.strip()).search(text) for p in phrases if p and p.strip()):
            found.append(cand["id"])
    return found

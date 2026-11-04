"""Give roll-call votes the topics of the bill they voted on (D-020, spec §5 topic tagging)."""

from __future__ import annotations

import re

CROSSWALK_TAG = "crosswalk@1"


def normalize_bill_number(value: str | None) -> str | None:
    """'H.R.1', 'HR 1' and 'HR1' all become 'HR1'."""
    if not value:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    return cleaned or None


def tag_votes_from_bills(votes: list[dict], bills: list[dict]) -> list[dict]:
    """Return votes with topics and policy_area copied from the matching bill.

    A match is the same congress and the same normalized bill number. Votes with no
    matching bill are returned unchanged.
    """
    by_key: dict[tuple[int, str], dict] = {}
    for b in bills:
        key = normalize_bill_number(b.get("bill_number"))
        if key:
            by_key.setdefault((b["congress"], key), b)

    out = []
    for v in votes:
        key = normalize_bill_number(v.get("bill_number"))
        match = by_key.get((v.get("congress"), key)) if key else None
        if match is None:
            out.append(v)
            continue
        tagged = dict(v)
        tagged["policy_area"] = match.get("policy_area")
        if match.get("topics"):
            tagged["topics"] = list(match["topics"])
            tagged["tagged_by"] = CROSSWALK_TAG
        out.append(tagged)
    return out


def retag_votes(root) -> int:
    """Apply bill topics to every vote under root. Return how many vote files changed."""
    from pathlib import Path

    from tracker.records import load_records, write_record

    root = Path(root)
    bills = list(load_records(root, "bill"))
    votes = list(load_records(root, "vote"))
    changed = 0
    for old, new in zip(votes, tag_votes_from_bills(votes, bills)):
        if new != old:
            changed += write_record(new, root)
    return changed


if __name__ == "__main__":
    import sys

    print(f"{retag_votes(sys.argv[1] if len(sys.argv) > 1 else 'data')} vote record(s) retagged")

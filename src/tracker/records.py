"""Read and write record JSON files, one record per file."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

TYPE_DIRS: dict[str, str] = {
    "candidate": "candidates",
    "finance": "finance",
    "vote": "record",
    "executive_action": "executive-actions",
    "outside_spending": "finance",
    "bill": "record",
    "bio": "bio",
}


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_path(record: dict, root: Path) -> Path:
    root = Path(root)
    if record["type"] == "candidate":
        return root / "candidates" / f"{record['id']}.json"
    return root / TYPE_DIRS[record["type"]] / record["candidate_ids"][0] / f"{record['id']}.json"


def _content(record: dict) -> dict:
    return {k: v for k, v in record.items() if k != "collected_at"}


def write_record(record: dict, root: Path) -> bool:
    """Write the record. Return False and leave the file alone if only collected_at differs."""
    path = record_path(record, root)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if _content(existing) == _content(record):
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def load_records(root: Path, type: str | None = None) -> Iterator[dict]:
    """Yield records of one type, or every type. Types may share a folder (finance)."""
    root = Path(root)
    wanted = {type} if type is not None else set(TYPE_DIRS)
    seen_dirs: set[str] = set()
    for t in TYPE_DIRS:
        if t not in wanted or TYPE_DIRS[t] in seen_dirs:
            continue
        seen_dirs.add(TYPE_DIRS[t])
        base = root / TYPE_DIRS[t]
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("type") in wanted:
                yield record

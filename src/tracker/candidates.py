"""Sync candidate records from config/candidates.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from tracker.records import now_iso, write_record
from tracker.validate import REPO_ROOT, validate_record

COLLECTOR = "candidates@1.0"
FEC_CANDIDATE_URL = "https://www.fec.gov/data/candidate/{fec_id}/"
CONFIG_PATH = REPO_ROOT / "config" / "candidates.yaml"
DATA_DIR = REPO_ROOT / "data"

# Replaced by `candidacies` in candidate model v2 (D-006). Old configs fail loudly.
RETIRED_KEYS = ("status", "party")


def load_config(path: Path) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return list(data.get("candidates", []))


def _source_url(entry: dict) -> str | None:
    if entry.get("official_site"):
        return entry["official_site"]
    fec_ids = entry.get("fec_candidate_ids") or []
    if fec_ids:
        return FEC_CANDIDATE_URL.format(fec_id=fec_ids[0])
    return None


def _build(entry: dict) -> dict:
    cid = entry["id"]
    for key in RETIRED_KEYS:
        if key in entry:
            raise ValueError(f"{cid}: '{key}' is retired; use 'candidacies' (one entry per election)")
    return {
        "id": cid,
        "type": "candidate",
        "candidate_ids": [cid],
        "source_url": _source_url(entry),
        # as_of, not today's date: reruns must stay byte-identical (see write_record).
        "published_at": str(entry["as_of"]),
        "collected_at": now_iso(),
        "collector": COLLECTOR,
        "topics": [],
        "name": entry["name"],
        "aliases": entry.get("aliases") or [],
        "social_accounts": entry.get("social_accounts") or [],
        "candidacies": entry.get("candidacies") or [],
        "fec_candidate_ids": entry.get("fec_candidate_ids") or [],
        "icpsr": entry.get("icpsr"),
        "bioguide_id": entry.get("bioguide_id"),
        "official_site": entry.get("official_site"),
        "inclusion_reason": entry["inclusion_reason"],
        "disclosure_names": entry.get("disclosure_names") or [],
    }


def sync_candidates(config_path: Path, root: Path) -> int:
    """Write candidate records for every config entry. Return how many files changed."""
    entries = load_config(config_path)

    seen: set[str] = set()
    for entry in entries:
        if entry["id"] in seen:
            raise ValueError(f"duplicate candidate id: {entry['id']}")
        seen.add(entry["id"])

    records = []
    for entry in entries:
        record = _build(entry)
        errors = validate_record(record)
        if errors:
            raise ValueError(f"{entry['id']}: " + "; ".join(errors))
        records.append(record)

    return sum(write_record(r, root) for r in records)


def main() -> int:
    changed = sync_candidates(CONFIG_PATH, DATA_DIR)
    print(f"{changed} candidate record(s) written or updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

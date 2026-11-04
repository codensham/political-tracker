"""Validate record files against the JSON Schemas and the topic taxonomy."""

from __future__ import annotations

import json
import sys
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tracker.records import TYPE_DIRS, record_path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"
TAXONOMY_PATH = REPO_ROOT / "taxonomy" / "topics.json"


@cache
def _schema_for(record_type: str) -> Draft202012Validator:
    base = json.loads((SCHEMA_DIR / "base.schema.json").read_text(encoding="utf-8"))
    typed = json.loads((SCHEMA_DIR / f"{record_type}.schema.json").read_text(encoding="utf-8"))
    combined = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "allOf": [base, typed],
        "unevaluatedProperties": False,
    }
    return Draft202012Validator(combined, format_checker=FormatChecker())


@cache
def _topic_ids() -> frozenset[str]:
    data = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    return frozenset(t["id"] for t in data["topics"])


def validate_record(record: dict) -> list[str]:
    """Return a list of error messages. An empty list means the record is valid."""
    if not isinstance(record, dict):
        return ["record is not a JSON object"]
    record_type = record.get("type")
    if record_type not in TYPE_DIRS:
        return [f"unknown record type: {record_type!r}"]

    errors = [
        f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
        for e in sorted(_schema_for(record_type).iter_errors(record), key=lambda e: list(e.path))
    ]

    for topic in record.get("topics", []):
        if not isinstance(topic, str) or topic not in _topic_ids():
            errors.append(f"topics: unknown topic {topic!r}")

    if (
        record_type == "bio"
        and isinstance(record.get("end_date"), str)
        and isinstance(record.get("start_date"), str)
    ):
        if record["end_date"] < record["start_date"]:
            errors.append("end_date: before start_date")

    if record_type == "candidate" and record.get("id") not in record.get("candidate_ids", []):
        errors.append("candidate_ids: must contain the candidate's own id")

    return errors


def validate_tree(root: Path) -> dict[Path, list[str]]:
    """Validate every file under root. Return only the files that have errors.

    Fails closed: a file with no schema (unknown folder, non-JSON) is an error, so
    nothing unvalidated can ride along on an auto-merged pull request.
    """
    root = Path(root)
    report: dict[Path, list[str]] = {}
    known_dirs = set(TYPE_DIRS.values())
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(root)
        if rel.parts[0] not in known_dirs:
            report.setdefault(path, []).append(f"no schema for folder {rel.parts[0]!r}")
        elif path.suffix != ".json":
            report.setdefault(path, []).append("not a JSON record file")
    for dirname in dict.fromkeys(TYPE_DIRS.values()):
        base = root / dirname
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                report[path] = [f"invalid JSON: {exc}"]
                continue
            errors = validate_record(record)
            if not errors:
                expected = record_path(record, root)
                if path != expected:
                    errors.append(f"misplaced: expected {expected.relative_to(root)}")
            if errors:
                report[path] = errors
    return report


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m tracker.validate <data_dir>", file=sys.stderr)
        return 2
    report = validate_tree(Path(args[0]))
    for path, errors in report.items():
        for error in errors:
            print(f"{path}: {error}")
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())

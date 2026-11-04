"""Validate record files against the JSON Schemas and the topic taxonomy."""

from __future__ import annotations

import json
import sys
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tracker.records import TYPE_DIRS, load_records, record_path

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

    if (
        record_type == "poll"
        and isinstance(record.get("field_end"), str)
        and isinstance(record.get("field_start"), str)
        and record["field_end"] < record["field_start"]
    ):
        errors.append("field_end: before field_start")

    if record_type == "candidate" and record.get("id") not in record.get("candidate_ids", []):
        errors.append("candidate_ids: must contain the candidate's own id")

    return errors


def speaker_errors(record: dict, candidates: dict[str, dict]) -> list[str]:
    """D-037: a statement's speaker must be its candidate's name or an alias."""
    cid = record["candidate_ids"][0]
    cand = candidates.get(cid)
    if cand is None:
        return [f"speaker: no candidate record for {cid!r}"]
    allowed = {cand["name"], *cand.get("aliases", [])}
    if record.get("speaker") not in allowed:
        return [f"speaker: {record.get('speaker')!r} is not a name or alias of {cid}"]
    return []


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
    candidates = {c["id"]: c for c in load_records(root, "candidate")}
    seen: dict[tuple, list[Path]] = {}
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
            if not errors and record.get("type") == "statement":
                errors += speaker_errors(record, candidates)
            if not errors:
                expected = record_path(record, root)
                if path != expected:
                    errors.append(f"misplaced: expected {expected.relative_to(root)}")
            if errors:
                report[path] = errors
            elif (key := duplicate_keys(record)) is not None:
                seen.setdefault(key, []).append(path)
    for paths in seen.values():
        if len(paths) > 1:
            for path in paths:
                others = [p.relative_to(root).as_posix() for p in paths if p != path]
                report.setdefault(path, []).append(f"duplicate of {', '.join(others)}")
    return report


def duplicate_keys(record: dict) -> tuple | None:
    """Identity of a record for duplicate detection (spec §6). Two records with the same key are the
    same evidence entered twice. None means the type has no duplicate rule."""
    rtype = record.get("type")
    url = record.get("source_url")
    if rtype == "statement":
        return ("statement", url, normalize_text(record.get("quote", "")))
    if rtype == "article":
        return ("article", url)
    if rtype == "endorsement":
        return ("endorsement", url, record.get("endorser"))
    if rtype == "appearance":
        return ("appearance", url, record.get("event"))
    if rtype == "poll":
        return ("poll", url, record.get("pollster"), record.get("field_end"))
    return None


def normalize_text(text: str) -> str:
    return " ".join(text.split()).lower()


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

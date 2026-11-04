"""The only write path for Claude-assisted skills (spec §6, Phase 13).

A skill proposes records; write_checked refuses anything that breaks the rules, then writes through
write_record. Stance-like fields, records without a source_url, and schema-invalid records are never
written.
"""

from __future__ import annotations

from pathlib import Path

from tracker.records import write_record
from tracker.validate import validate_record

# CLAUDE.md: never add stance, sentiment, summary or verdict fields.
FORBIDDEN_FIELDS = ("stance", "sentiment", "summary", "verdict")


def write_checked(record: dict, root: Path) -> bool:
    """Validate and write one record. Return True if the file changed, False if it was unchanged.

    Raises ValueError and writes nothing if the record has a forbidden field, no source_url,
    or fails the schema.
    """
    for field in FORBIDDEN_FIELDS:
        if field in record:
            raise ValueError(f"forbidden field {field!r}: records carry evidence, not characterization")
    if not record.get("source_url"):
        raise ValueError("source_url is required on every record")
    errors = validate_record(record)
    if errors:
        raise ValueError(f"{record.get('id')}: " + "; ".join(errors))
    return write_record(record, Path(root))

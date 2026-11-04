"""Collector protocol and the runner that stamps, validates and writes records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from tracker.records import load_records, now_iso, write_record
from tracker.validate import validate_record


class Collector(Protocol):
    name: str
    version: str

    def collect(self, candidates: list[dict]) -> Iterable[dict]: ...


class InvalidRecord(ValueError):
    def __init__(self, record_id: str | None, errors: list[str]):
        super().__init__(f"{record_id}: " + "; ".join(errors))
        self.errors = errors


@dataclass
class RunResult:
    written: int = 0
    unchanged: int = 0


def run_collector(c: Collector, root: Path) -> RunResult:
    root = Path(root)
    candidates = list(load_records(root, "candidate"))
    collector_id = f"{c.name}@{c.version}"
    collected_at = now_iso()
    result = RunResult()

    for raw in c.collect(candidates):
        record = {**raw, "collector": collector_id, "collected_at": collected_at}
        errors = validate_record(record)
        if errors:
            raise InvalidRecord(record.get("id"), errors)
        if write_record(record, root):
            result.written += 1
        else:
            result.unchanged += 1

    return result

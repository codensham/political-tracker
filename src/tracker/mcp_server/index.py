"""In-memory index over the record files, used by the MCP tools."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from tracker.records import load_records

NON_EVIDENCE_TYPES = frozenset({"candidate", "finance"})


class UnknownCandidate(LookupError):
    def __init__(self, candidate_id: str, valid_ids: Iterable[str]):
        valid = sorted(valid_ids)
        listing = ", ".join(valid) if valid else "(none loaded)"
        super().__init__(f"unknown candidate {candidate_id!r}; valid ids: {listing}")
        self.candidate_id = candidate_id


class DataIndex:
    def __init__(self, candidates: list[dict], records: list[dict]):
        self._candidates = {c["id"]: c for c in candidates}
        self._records = records

    @classmethod
    def load(cls, root: Path) -> DataIndex:
        root = Path(root)
        candidates = list(load_records(root, "candidate"))
        records = [r for r in load_records(root) if r["type"] != "candidate"]
        return cls(candidates, records)

    def candidates(self, status: str | None = None) -> list[dict]:
        found = [c for c in self._candidates.values() if status is None or c.get("status") == status]
        return sorted(found, key=lambda c: c["id"])

    def candidate(self, candidate_id: str) -> dict:
        if candidate_id not in self._candidates:
            raise UnknownCandidate(candidate_id, self._candidates)
        return self._candidates[candidate_id]

    def _records_for(self, candidate_id: str) -> list[dict]:
        self.candidate(candidate_id)
        return [r for r in self._records if candidate_id in r.get("candidate_ids", [])]

    def evidence(
        self,
        candidate_id: str,
        topic: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        types: list[str] | None = None,
    ) -> list[dict]:
        found = []
        for r in self._records_for(candidate_id):
            if r["type"] in NON_EVIDENCE_TYPES:
                continue
            if types and r["type"] not in types:
                continue
            if topic is not None and topic not in r.get("topics", []):
                continue
            if date_from and r["published_at"] < date_from:
                continue
            if date_to and r["published_at"] > date_to:
                continue
            found.append(r)
        return sorted(found, key=lambda r: (r["published_at"], r["id"]))

    def finance(self, candidate_id: str, cycle: int | None = None) -> list[dict]:
        found = [
            r
            for r in self._records_for(candidate_id)
            if r["type"] == "finance" and (cycle is None or r["cycle"] == cycle)
        ]
        return sorted(found, key=lambda r: (r["coverage_end"], r["id"]))

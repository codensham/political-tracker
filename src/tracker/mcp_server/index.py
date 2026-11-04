"""In-memory index over the record files, used by the MCP tools."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from tracker.mcp_server.cache import load_records_cached

# Spec §6: what search_evidence covers. Finance, outside spending, bios and disclosures are
# served by their own tools.
EVIDENCE_TYPES = frozenset(
    {
        "statement",
        "position",
        "vote",
        "bill",
        "executive_action",
        "article",
        "endorsement",
        "appearance",
        "poll",
    }
)

# position_timeline: what a candidate said, published, voted or signed on a topic.
TIMELINE_TYPES = ("statement", "position", "vote", "bill", "executive_action")


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
    def load(cls, root: Path, cache_path: Path | None = None) -> DataIndex:
        root = Path(root)
        records = load_records_cached(root, cache_path)
        candidates = [r for r in records if r["type"] == "candidate"]
        others = [r for r in records if r["type"] != "candidate"]
        return cls(candidates, others)

    def candidates(
        self,
        office: str | None = None,
        year: int | None = None,
        result: str | None = None,
    ) -> list[dict]:
        """Candidates with at least one candidacy matching every filter given."""

        def matches(c: dict) -> bool:
            return any(
                (office is None or k.get("office") == office)
                and (year is None or k.get("year") == year)
                and (result is None or k.get("result") == result)
                for k in c.get("candidacies", [])
            )

        found = [c for c in self._candidates.values() if matches(c)]
        return sorted(found, key=lambda c: c["id"])

    def candidate(self, candidate_id: str) -> dict:
        if candidate_id not in self._candidates:
            raise UnknownCandidate(candidate_id, self._candidates)
        return self._candidates[candidate_id]

    def _records_for(self, candidate_id: str) -> list[dict]:
        self.candidate(candidate_id)
        return [r for r in self._records if candidate_id in r.get("candidate_ids", [])]

    def _typed(self, candidate_id: str, record_type: str, key: Callable[[dict], Any]) -> list[dict]:
        found = [r for r in self._records_for(candidate_id) if r["type"] == record_type]
        return sorted(found, key=key)

    def evidence(
        self,
        candidate_id: str,
        topic: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        types: list[str] | None = None,
    ) -> list[dict]:
        allowed = EVIDENCE_TYPES if types is None else EVIDENCE_TYPES & set(types)
        found = []
        for r in self._records_for(candidate_id):
            if r["type"] not in allowed:
                continue
            if topic is not None and topic not in r.get("topics", []):
                continue
            if date_from and r["published_at"] < date_from:
                continue
            if date_to and r["published_at"] > date_to:
                continue
            found.append(r)
        return sorted(found, key=lambda r: (r["published_at"], r["id"]))

    def position_timeline(self, candidate_id: str, topic: str) -> list[dict]:
        return self.evidence(candidate_id, topic=topic, types=list(TIMELINE_TYPES))

    def compare(self, candidate_ids: list[str], topic: str) -> list[dict]:
        """One group per candidate, in the order given. Nothing is ranked."""
        for cid in candidate_ids:
            self.candidate(cid)
        return [
            {
                "candidate_id": cid,
                "evidence": self.position_timeline(cid, topic),
            }
            for cid in candidate_ids
        ]

    def finance(self, candidate_id: str, cycle: int | None = None) -> list[dict]:
        found = [
            r
            for r in self._records_for(candidate_id)
            if r["type"] == "finance" and (cycle is None or r["cycle"] == cycle)
        ]
        return sorted(found, key=lambda r: (r["coverage_end"], r["id"]))

    def outside_spending(self, candidate_id: str, cycle: int | None = None) -> list[dict]:
        found = [
            r
            for r in self._typed(candidate_id, "outside_spending", lambda r: (r["cycle"], r["id"]))
            if cycle is None or r["cycle"] == cycle
        ]
        return found

    def bio(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "bio", lambda r: (r.get("start_date") or "", r["id"]))

    def disclosures(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "disclosure", lambda r: (r["filing_date"], r["id"]))

    def endorsements(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "endorsement", lambda r: (r["date"], r["id"]))

    def appearances(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "appearance", lambda r: (r["date"], r["id"]))

    def polls(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "poll", lambda r: (r["field_end"], r["id"]))

    def positions(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "position", lambda r: (r["capture_date"], r["id"]))

    def bills(self, candidate_id: str) -> list[dict]:
        return self._typed(candidate_id, "bill", lambda r: (r["published_at"], r["id"]))

    def media_attention(
        self,
        candidate_id: str | None = None,
        outlet_id: str | None = None,
        period: str | None = None,
    ) -> list[dict]:
        """Article counts per candidate and outlet, computed on every call from the article records.

        period is a prefix of published_at: "2024" for a year, "2024-10" for a month.
        """
        if candidate_id is not None:
            self.candidate(candidate_id)
        groups: dict[tuple[str, str], list[str]] = {}
        for r in self._records:
            if r["type"] != "article":
                continue
            if outlet_id is not None and r["outlet_id"] != outlet_id:
                continue
            if period is not None and not r["published_at"].startswith(period):
                continue
            for cid in r["candidate_ids"]:
                if candidate_id is not None and cid != candidate_id:
                    continue
                groups.setdefault((cid, r["outlet_id"]), []).append(r["id"])
        return [
            {
                "candidate_id": cid,
                "outlet_id": outlet,
                "article_count": len(ids),
                "article_ids": sorted(ids),
            }
            for (cid, outlet), ids in sorted(groups.items())
        ]

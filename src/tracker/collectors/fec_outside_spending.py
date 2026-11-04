"""FEC outside spending collector: independent expenditures (Schedule E) aggregated by committee.

One record per candidate, FEC candidate ID, cycle, committee, and support/oppose direction.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable

import httpx

from tracker.collectors import REGISTRY
from tracker.config import get_key
from tracker.http import get_json

BASE_URL = "https://api.open.fec.gov/v1"
ENDPOINT = f"{BASE_URL}/schedules/schedule_e/by_candidate/"
PER_PAGE = 100
DIRECTIONS = {"S": "support", "O": "oppose"}


class FecOutsideSpendingCollector:
    name = "fec_outside_spending"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=30)
        self._sleep = sleep
        self._api_key = get_key("FEC_API_KEY") or "DEMO_KEY"

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        for cand in candidates:
            cycles = sorted({k["year"] for k in cand.get("candidacies", [])})
            for fec_id in cand.get("fec_candidate_ids") or []:
                for cycle in cycles:
                    yield from self._cycle_rows(cand["id"], fec_id, cycle)

    def _cycle_rows(self, candidate_id: str, fec_id: str, cycle: int) -> Iterable[dict]:
        page = 1
        while True:
            payload = get_json(
                self._client,
                ENDPOINT,
                {
                    "api_key": self._api_key,
                    "candidate_id": fec_id,
                    "cycle": cycle,
                    "per_page": PER_PAGE,
                    "page": page,
                },
                sleep=self._sleep,
            )
            for row in payload.get("results", []):
                record = _to_record(candidate_id, fec_id, cycle, row)
                if record is not None:
                    yield record
            pages = (payload.get("pagination") or {}).get("pages") or 1
            if page >= pages:
                return
            page += 1


def _to_record(candidate_id: str, fec_id: str, cycle: int, row: dict) -> dict | None:
    direction = DIRECTIONS.get(row.get("support_oppose_indicator"))
    total = row.get("total")
    committee_id = row.get("committee_id")
    # Rows without a direction, amount or committee cannot form a valid record. Skip them.
    if direction is None or total is None or not committee_id:
        return None
    return {
        "id": f"outside-{candidate_id}-{fec_id.lower()}-{cycle}-{committee_id.lower()}-{direction}",
        "type": "outside_spending",
        "candidate_ids": [candidate_id],
        "source_url": f"https://www.fec.gov/data/candidate/{fec_id}/?cycle={cycle}",
        # Schedule E totals carry no per-filing date. The cycle end is the stable date.
        "published_at": f"{cycle}-12-31",
        "topics": [],
        "cycle": cycle,
        "support_oppose": direction,
        "amount": float(total),
        "committee_id": committee_id,
        "committee_name": row.get("committee_name") or committee_id,
        "fec_candidate_id": fec_id,
    }


REGISTRY["fec_outside_spending"] = FecOutsideSpendingCollector

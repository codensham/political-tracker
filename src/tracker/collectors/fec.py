"""FEC finance collector: candidate totals per cycle, one finance record per result row."""

from __future__ import annotations

import os
import time
from typing import Callable, Iterable

import httpx

from tracker.collectors import REGISTRY
from tracker.http import get_json

BASE_URL = "https://api.open.fec.gov/v1"


class FecFinanceCollector:
    name = "fec_finance"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=30)
        self._sleep = sleep
        self._api_key = os.environ.get("FEC_API_KEY") or "DEMO_KEY"

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        for cand in candidates:
            for fec_id in cand.get("fec_candidate_ids") or []:
                payload = get_json(
                    self._client,
                    f"{BASE_URL}/candidate/{fec_id}/totals/",
                    {"api_key": self._api_key, "per_page": 100},
                    sleep=self._sleep,
                )
                for row in payload.get("results", []):
                    yield _to_record(cand["id"], fec_id, row)


def _to_record(candidate_id: str, fec_id: str, row: dict) -> dict:
    cycle = row["cycle"]
    coverage_end = row["coverage_end_date"][:10]
    return {
        "id": f"finance-{candidate_id}-{fec_id.lower()}-{cycle}",
        "type": "finance",
        "candidate_ids": [candidate_id],
        "source_url": f"https://www.fec.gov/data/candidate/{fec_id}/?cycle={cycle}",
        "published_at": coverage_end,
        "topics": [],
        "cycle": cycle,
        "receipts": row["receipts"],
        "disbursements": row["disbursements"],
        "cash_on_hand_end": row["last_cash_on_hand_end_period"],
        "debts_owed": row["last_debts_owed_by_committee"],
        "coverage_start": row["coverage_start_date"][:10],
        "coverage_end": coverage_end,
        "fec_candidate_id": fec_id,
    }


REGISTRY["fec_finance"] = FecFinanceCollector

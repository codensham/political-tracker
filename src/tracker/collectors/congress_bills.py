"""Congress.gov bills: legislation each tracked member sponsored or cosponsored.

Official records, no judgment involved. Topics come from the policy-area crosswalk (D-020).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable

import httpx

from tracker.collectors import REGISTRY
from tracker.config import get_key
from tracker.crosswalk import topics_for
from tracker.http import get_json

BASE_URL = "https://api.congress.gov/v3"
PAGE = 250
CROSSWALK_TAG = "crosswalk@1"

# Congress.gov bill type -> slug used in its public URLs.
BILL_SLUGS = {
    "HR": "house-bill",
    "S": "senate-bill",
    "HRES": "house-resolution",
    "SRES": "senate-resolution",
    "HJRES": "house-joint-resolution",
    "SJRES": "senate-joint-resolution",
    "HCONRES": "house-concurrent-resolution",
    "SCONRES": "senate-concurrent-resolution",
}

LISTS = (
    ("sponsored-legislation", "sponsoredLegislation", "sponsor"),
    ("cosponsored-legislation", "cosponsoredLegislation", "cosponsor"),
)


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def bill_url(congress: int, bill_type: str, number: str) -> str:
    slug = BILL_SLUGS[bill_type]
    return f"https://www.congress.gov/bill/{_ordinal(congress)}-congress/{slug}/{number}"


class CongressBillsCollector:
    name = "congress_bills"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=30)
        self._sleep = sleep
        self._api_key = get_key("CONGRESS_API_KEY") or "DEMO_KEY"

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        for cand in candidates:
            bioguide = cand.get("bioguide_id")
            if not bioguide:
                continue
            for endpoint, key, role in LISTS:
                offset = 0
                while True:
                    payload = get_json(
                        self._client,
                        f"{BASE_URL}/member/{bioguide}/{endpoint}",
                        {"api_key": self._api_key, "limit": PAGE, "offset": offset, "format": "json"},
                        sleep=self._sleep,
                    )
                    rows = payload.get(key) or []
                    for row in rows:
                        record = _to_record(cand["id"], role, row)
                        if record is not None:
                            yield record
                    if not (payload.get("pagination") or {}).get("next") or not rows:
                        break
                    offset += PAGE


def _to_record(candidate_id: str, role: str, row: dict) -> dict | None:
    bill_type = row.get("type")
    number = row.get("number")
    congress = row.get("congress")
    introduced = row.get("introducedDate")
    # Amendments carry no bill type. Unknown types have no public URL. Skip both.
    if not bill_type or bill_type not in BILL_SLUGS or number is None or congress is None or not introduced:
        return None
    number = str(number)
    policy_area = (row.get("policyArea") or {}).get("name")
    topics = topics_for(policy_area)
    record = {
        "id": f"bill-{congress}-{bill_type.lower()}-{number}-{candidate_id}",
        "type": "bill",
        "candidate_ids": [candidate_id],
        "source_url": bill_url(int(congress), bill_type, number),
        "published_at": introduced,
        "topics": topics,
        "congress": int(congress),
        "bill_number": f"{bill_type}{number}",
        "title": row.get("title") or f"{bill_type} {number}",
        "policy_area": policy_area,
        "role": role,
        "introduced_date": introduced,
    }
    if topics:
        record["tagged_by"] = CROSSWALK_TAG
    return record


REGISTRY["congress_bills"] = CongressBillsCollector

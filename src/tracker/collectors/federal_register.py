"""Federal Register collector: executive orders, proclamations and memoranda signed by a tracked president.

These are official, public-domain records and feed the track record. No API key is needed.
"""

from __future__ import annotations

import time
from typing import Callable, Iterable

import httpx

from tracker.collectors import REGISTRY
from tracker.http import get_json

API_URL = "https://www.federalregister.gov/api/v1/documents.json"

# Tracked candidate id -> Federal Register president identifier. Set by hand, never inferred.
PRESIDENT_SLUGS: dict[str, str] = {"donald-trump": "donald-trump"}

DOCUMENT_TYPES = ("executive_order", "proclamation", "memorandum")

FIELDS = [
    "document_number",
    "title",
    "publication_date",
    "signing_date",
    "html_url",
    "executive_order_number",
]


class FederalRegisterCollector:
    name = "federal_register"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=30)
        self._sleep = sleep

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        for cand in candidates:
            slug = PRESIDENT_SLUGS.get(cand["id"])
            if slug is None:
                continue
            for doc_type in DOCUMENT_TYPES:
                url: str | None = API_URL
                params: dict | None = {
                    "conditions[president]": slug,
                    "conditions[presidential_document_type][]": doc_type,
                    "per_page": 1000,
                    "order": "oldest",
                    "fields[]": FIELDS,
                }
                while url:
                    payload = get_json(self._client, url, params, sleep=self._sleep)
                    for row in payload.get("results", []):
                        yield _to_record(cand["id"], doc_type, row)
                    # Later pages carry their query string in next_page_url.
                    url = payload.get("next_page_url")
                    params = None


def _to_record(candidate_id: str, doc_type: str, row: dict) -> dict:
    number = row["document_number"]
    return {
        "id": f"exec-{number.lower()}",
        "type": "executive_action",
        "candidate_ids": [candidate_id],
        "source_url": row["html_url"],
        "published_at": row["publication_date"],
        "topics": [],
        "document_type": doc_type,
        "document_number": number,
        "title": row["title"],
        "signing_date": row.get("signing_date"),
        "executive_order_number": row.get("executive_order_number"),
    }


REGISTRY["federal_register"] = FederalRegisterCollector

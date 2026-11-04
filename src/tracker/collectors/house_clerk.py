"""House Clerk collector: annual House financial-disclosure index, matched by exact filer name.

The index is a public zip of XML rows, one per filing. A filer is matched only when the name
built from First, Last and Suffix equals a string in the candidate's `disclosure_names` (no fuzzy
matching). Official tier: records are written under data/disclosures/<cid>/.
"""

from __future__ import annotations

import io
import time
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable, Iterable
from datetime import date, datetime

import httpx

from tracker.collectors import REGISTRY
from tracker.http import get_bytes

BASE_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs"


def index_url(year: int) -> str:
    return f"{BASE_URL}/{year}FD.zip"


def document_url(year: int, doc_id: str) -> str:
    return f"{BASE_URL}/{year}/{doc_id}.pdf"


def _filer_name(row: dict[str, str]) -> str:
    return " ".join(part for part in (row.get("First"), row.get("Last"), row.get("Suffix")) if part)


def _rows(zip_bytes: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_name = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
        root = ET.fromstring(zf.read(xml_name))
    rows = []
    for member in root.iter("Member"):
        row = {child.tag: (child.text or "").strip() for child in member}
        row["name"] = _filer_name(row)
        rows.append(row)
    return rows


def _to_record(candidate_id: str, year: int, row: dict[str, str]) -> dict:
    filing_date = datetime.strptime(row["FilingDate"], "%m/%d/%Y").date().isoformat()
    doc_id = row["DocID"]
    return {
        "id": f"disclosure-{candidate_id}-{year}-{doc_id}",
        "type": "disclosure",
        "candidate_ids": [candidate_id],
        "source_url": document_url(year, doc_id),
        "published_at": filing_date,
        "topics": [],
        "filer_name": row["name"],
        "year": year,
        "form": row["FilingType"],
        "filing_date": filing_date,
        "document_url": document_url(year, doc_id),
    }


class HouseClerkCollector:
    name = "house_clerk"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        years: list[int] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=60)
        self._years = years if years is not None else [date.today().year]
        self._sleep = sleep

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        watch: dict[str, list[str]] = {}
        for cand in candidates:
            for name in cand.get("disclosure_names") or []:
                watch.setdefault(name, []).append(cand["id"])
        if not watch:
            return
        for year in self._years:
            data = get_bytes(self._client, index_url(year), sleep=self._sleep)
            for row in _rows(data):
                for cid in watch.get(row["name"], []):
                    yield _to_record(cid, year, row)


REGISTRY["house_clerk"] = HouseClerkCollector

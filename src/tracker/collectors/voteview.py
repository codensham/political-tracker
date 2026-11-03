"""Voteview collector: every roll-call vote cast by a tracked member, for their whole career."""

from __future__ import annotations

import csv
import io
import time
from pathlib import Path
from typing import Callable, Iterable

import httpx

from tracker.collectors import REGISTRY
from tracker.http import get_bytes
from tracker.validate import REPO_ROOT

BASE_URL = "https://voteview.com/static/data/out"
MEMBERS_PATH = "members/HSall_members.csv"
CHAMBER_LETTER = {"House": "H", "Senate": "S"}


def map_cast(code: int) -> str | None:
    """Voteview cast_code to our cast values. 0 means not a member at the time: no record."""
    if 1 <= code <= 3:
        return "yea"
    if 4 <= code <= 6:
        return "nay"
    if 7 <= code <= 8:
        return "present"
    if code == 9:
        return "not_voting"
    return None


class VoteviewCollector:
    name = "voteview"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        cache_dir: Path | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=120, follow_redirects=True)
        self._cache = Path(cache_dir) if cache_dir else REPO_ROOT / ".cache" / "voteview"
        self._sleep = sleep
        self._members: list[dict] | None = None

    def _fetch(self, relpath: str) -> str:
        path = self._cache / relpath
        if not path.exists():
            data = get_bytes(self._client, f"{BASE_URL}/{relpath}", sleep=self._sleep)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return path.read_text(encoding="utf-8")

    def _member_rows(self) -> list[dict]:
        if self._members is None:
            self._members = list(csv.DictReader(io.StringIO(self._fetch(MEMBERS_PATH))))
        return self._members

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        for cand in candidates:
            icpsr = cand.get("icpsr")
            if icpsr is None:
                continue
            icpsr = str(icpsr)
            for row in self._member_rows():
                if row["icpsr"] != icpsr or row["chamber"] not in CHAMBER_LETTER:
                    continue
                yield from self._votes(cand["id"], icpsr, CHAMBER_LETTER[row["chamber"]], int(row["congress"]))

    def _votes(self, candidate_id: str, icpsr: str, letter: str, congress: int) -> Iterable[dict]:
        name = f"{letter}{congress:03d}"
        rollcalls = {
            r["rollnumber"]: r
            for r in csv.DictReader(io.StringIO(self._fetch(f"rollcalls/{name}_rollcalls.csv")))
        }
        for row in csv.DictReader(io.StringIO(self._fetch(f"votes/{name}_votes.csv"))):
            if row["icpsr"] != icpsr:
                continue
            cast = map_cast(int(row["cast_code"]))
            roll = rollcalls.get(row["rollnumber"])
            if cast is None or roll is None:
                continue
            yield _to_record(candidate_id, letter, congress, int(row["rollnumber"]), cast, roll)


def _to_record(candidate_id: str, letter: str, congress: int, rollnumber: int, cast: str, roll: dict) -> dict:
    date = roll["date"]
    return {
        "id": f"vote-{letter.lower()}{congress}-{rollnumber}-{candidate_id}",
        "type": "vote",
        "candidate_ids": [candidate_id],
        "source_url": f"https://voteview.com/rollcall/R{letter}{congress:03d}{rollnumber:04d}",
        "published_at": date,
        "topics": [],
        "chamber": "house" if letter == "H" else "senate",
        "congress": congress,
        "rollnumber": rollnumber,
        "vote_date": date,
        "question": roll["vote_question"] or None,
        "bill_number": roll["bill_number"] or None,
        "vote_result": roll["vote_result"] or None,
        "cast": cast,
    }


REGISTRY["voteview"] = VoteviewCollector

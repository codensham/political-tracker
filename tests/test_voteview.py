import csv
import io
from pathlib import Path

import httpx
import pytest

from tracker.collectors import REGISTRY
from tracker.collectors.voteview import VoteviewCollector, map_cast
from tracker.validate import validate_record

FIX = Path(__file__).parent / "fixtures" / "voteview"
PREFIX = "https://voteview.com/static/data/out/"
FILES = {
    "members/HSall_members.csv": FIX / "HSall_members.csv",
    "votes/H115_votes.csv": FIX / "H115_votes.csv",
    "rollcalls/H115_rollcalls.csv": FIX / "H115_rollcalls.csv",
    "votes/S117_votes.csv": FIX / "S117_votes.csv",
    "rollcalls/S117_rollcalls.csv": FIX / "S117_rollcalls.csv",
}
CAND = {
    "id": "marsha-blackburn",
    "type": "candidate",
    "candidate_ids": ["marsha-blackburn"],
    "icpsr": 20351,
    "fec_candidate_ids": [],
}


def fixture_client(calls: list[str] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path.removeprefix("/static/data/out/")
        if calls is not None:
            calls.append(key)
        if key not in FILES:
            return httpx.Response(404, content=b"")
        return httpx.Response(200, content=FILES[key].read_bytes())

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_cast_mapping():
    assert [map_cast(c) for c in range(10)] == [
        None,
        "yea", "yea", "yea",
        "nay", "nay", "nay",
        "present", "present",
        "not_voting",
    ]


def test_join_and_fields(tmp_path: Path):
    records = list(
        VoteviewCollector(fixture_client(), cache_dir=tmp_path).collect([CAND])
    )
    by_id = {r["id"]: r for r in records}
    assert len(records) == 12

    rec = by_id["vote-s117-1-marsha-blackburn"]
    assert rec == {
        "id": "vote-s117-1-marsha-blackburn",
        "type": "vote",
        "candidate_ids": ["marsha-blackburn"],
        "source_url": "https://voteview.com/rollcall/RS1170001",
        "published_at": "2021-01-06",
        "topics": [],
        "chamber": "senate",
        "congress": 117,
        "rollnumber": 1,
        "vote_date": "2021-01-06",
        "question": "On the Objection",
        "bill_number": None,
        "vote_result": "Objection Not Sustained",
        "cast": "nay",
    }

    first_house = by_id["vote-h115-1-marsha-blackburn"]
    assert first_house["cast"] == "yea"
    assert first_house["chamber"] == "house"
    assert first_house["question"] == "Election of the Speaker"


def test_records_validate(tmp_path: Path):
    for rec in VoteviewCollector(fixture_client(), cache_dir=tmp_path).collect([CAND]):
        stamped = {**rec, "collector": "voteview@1.0", "collected_at": "2026-11-03T09:00:00Z"}
        assert validate_record(stamped) == []


def test_no_icpsr_skipped(tmp_path: Path):
    calls: list[str] = []
    no_icpsr = {**CAND, "icpsr": None}
    records = list(
        VoteviewCollector(fixture_client(calls), cache_dir=tmp_path).collect([no_icpsr])
    )
    assert records == []
    assert calls == []


def test_both_chambers(tmp_path: Path):
    records = list(
        VoteviewCollector(fixture_client(), cache_dir=tmp_path).collect([CAND])
    )
    assert {(r["chamber"], r["congress"]) for r in records} == {
        ("house", 115),
        ("senate", 117),
    }


def test_downloads_cached(tmp_path: Path):
    calls: list[str] = []
    list(VoteviewCollector(fixture_client(calls), cache_dir=tmp_path).collect([CAND]))
    assert len(calls) == 5

    later: list[str] = []
    list(VoteviewCollector(fixture_client(later), cache_dir=tmp_path).collect([CAND]))
    assert later == []


def test_registered():
    import tracker.collectors.voteview  # noqa: F401

    assert REGISTRY["voteview"] is VoteviewCollector

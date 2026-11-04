from pathlib import Path

import pytest

from tracker.collectors.base import InvalidRecord, RunResult, run_collector
from tracker.records import load_records, record_path, write_record


def vote(rid: str, **overrides):
    rec = {
        "id": rid,
        "type": "vote",
        "candidate_ids": ["jane-doe"],
        "source_url": f"https://voteview.com/rollcall/{rid}",
        "published_at": "2021-06-01",
        "topics": ["economy"],
        "chamber": "senate",
        "congress": 117,
        "rollnumber": 42,
        "vote_date": "2021-06-01",
        "cast": "yea",
    }
    rec.update(overrides)
    return rec


class FakeCollector:
    name = "fake"
    version = "1.0"

    def __init__(self, records):
        self._records = records
        self.seen_candidates = None

    def collect(self, candidates):
        self.seen_candidates = candidates
        for r in self._records:
            yield dict(r)


def test_run_writes_and_counts(tmp_path: Path):
    fake = FakeCollector([vote("vote-a"), vote("vote-b")])
    assert run_collector(fake, tmp_path) == RunResult(written=2, unchanged=0)

    stored = list(load_records(tmp_path, "vote"))
    assert {r["id"] for r in stored} == {"vote-a", "vote-b"}
    assert all(r["collector"] == "fake@1.0" for r in stored)
    assert all("collected_at" in r for r in stored)


def test_rerun_unchanged(tmp_path: Path):
    fake = FakeCollector([vote("vote-a"), vote("vote-b")])
    run_collector(fake, tmp_path)
    before = {
        rid: record_path(vote(rid), tmp_path).read_bytes() for rid in ("vote-a", "vote-b")
    }

    assert run_collector(fake, tmp_path) == RunResult(written=0, unchanged=2)
    after = {
        rid: record_path(vote(rid), tmp_path).read_bytes() for rid in ("vote-a", "vote-b")
    }
    assert before == after


def test_invalid_record_raises(tmp_path: Path):
    fake = FakeCollector([vote("vote-bad", topics=["not-a-topic"])])
    with pytest.raises(InvalidRecord, match="not-a-topic"):
        run_collector(fake, tmp_path)
    assert not record_path(vote("vote-bad"), tmp_path).exists()


def test_runner_passes_candidate_records(tmp_path: Path):
    candidate = {
        "id": "jane-doe",
        "type": "candidate",
        "candidate_ids": ["jane-doe"],
        "source_url": "https://janedoe.example/",
        "published_at": "2026-11-03",
        "collected_at": "2026-11-03T09:00:00Z",
        "collector": "candidates@1.0",
        "topics": [],
        "name": "Jane Doe",
        "party": "DEM",
        "status": "potential",
        "fec_candidate_ids": [],
        "icpsr": None,
        "bioguide_id": None,
        "official_site": "https://janedoe.example/",
        "inclusion_reason": "test",
    }
    write_record(candidate, tmp_path)
    fake = FakeCollector([])
    run_collector(fake, tmp_path)
    assert [c["id"] for c in fake.seen_candidates] == ["jane-doe"]

import json
from pathlib import Path

from tracker.records import load_records, record_path, write_record


def base(**overrides):
    rec = {
        "id": "vote-s117-42-jane-doe",
        "type": "vote",
        "candidate_ids": ["jane-doe"],
        "source_url": "https://voteview.com/rollcall/RS117000042",
        "published_at": "2021-06-01",
        "collected_at": "2026-11-03T09:00:00Z",
        "collector": "voteview@1.0",
        "topics": [],
        "cast": "yea",
    }
    rec.update(overrides)
    return rec


def test_candidate_path(tmp_path: Path):
    rec = base(id="jane-doe", type="candidate", candidate_ids=["jane-doe"])
    assert record_path(rec, tmp_path) == tmp_path / "candidates" / "jane-doe.json"


def test_vote_path(tmp_path: Path):
    rec = base()
    assert record_path(rec, tmp_path) == (
        tmp_path / "record" / "jane-doe" / "vote-s117-42-jane-doe.json"
    )


def test_roundtrip(tmp_path: Path):
    rec = base()
    assert write_record(rec, tmp_path) is True
    assert list(load_records(tmp_path, "vote")) == [rec]


def test_rewrite_ignores_collected_at(tmp_path: Path):
    rec = base()
    write_record(rec, tmp_path)
    path = record_path(rec, tmp_path)
    before = path.read_bytes()

    again = base(collected_at="2026-11-04T09:00:00Z")
    assert write_record(again, tmp_path) is False
    assert path.read_bytes() == before


def test_rewrite_detects_change(tmp_path: Path):
    write_record(base(), tmp_path)
    changed = base(vote_date="2021-06-02")
    assert write_record(changed, tmp_path) is True
    assert list(load_records(tmp_path, "vote")) == [changed]


def test_format(tmp_path: Path):
    rec = base()
    write_record(rec, tmp_path)
    text = record_path(rec, tmp_path).read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "\r" not in text
    parsed = json.loads(text)
    assert list(parsed) == sorted(parsed)

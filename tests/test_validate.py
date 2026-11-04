import json
import subprocess
import sys
from pathlib import Path

from tracker.records import write_record
from tracker.validate import validate_record, validate_tree


def vote(**overrides):
    rec = {
        "id": "vote-s117-42-jane-doe",
        "type": "vote",
        "candidate_ids": ["jane-doe"],
        "source_url": "https://voteview.com/rollcall/RS117000042",
        "published_at": "2021-06-01",
        "collected_at": "2026-11-03T09:00:00Z",
        "collector": "voteview@1.0",
        "topics": ["economy"],
        "chamber": "senate",
        "congress": 117,
        "rollnumber": 42,
        "vote_date": "2021-06-01",
        "question": "On Passage",
        "bill_number": "HR 1",
        "vote_result": "Passed",
        "cast": "yea",
    }
    rec.update(overrides)
    return rec


def candidate(**overrides):
    rec = {
        "id": "jane-doe",
        "type": "candidate",
        "candidate_ids": ["jane-doe"],
        "source_url": "https://www.fec.gov/data/candidate/P00000001/",
        "published_at": "2026-11-03",
        "collected_at": "2026-11-03T09:00:00Z",
        "collector": "candidates@1.0",
        "topics": [],
        "name": "Jane Doe",
        "aliases": ["Jane Doe"],
        "candidacies": [
            {
                "office": "president",
                "year": 2028,
                "party": "DEM",
                "result": "potential",
                "fec_candidate_id": "P00000001",
                "source_url": "https://www.fec.gov/data/candidate/P00000001/",
            }
        ],
        "fec_candidate_ids": ["P00000001"],
        "icpsr": 12345,
        "bioguide_id": None,
        "official_site": None,
        "inclusion_reason": "polls",
    }
    rec.update(overrides)
    return rec


def test_valid_vote_passes():
    assert validate_record(vote()) == []


def test_missing_source_url_fails():
    rec = vote()
    del rec["source_url"]
    errors = validate_record(rec)
    assert any("source_url" in e for e in errors)


def test_unknown_topic_fails():
    errors = validate_record(vote(topics=["not-a-topic"]))
    assert any("not-a-topic" in e for e in errors)


def test_stance_field_rejected():
    errors = validate_record(candidate(stance="supports X"))
    assert any("stance" in e for e in errors)


def test_bad_status_fails():
    errors = validate_record(
        candidate(
            candidacies=[
                {
                    "office": "president",
                    "year": 2028,
                    "party": "DEM",
                    "result": "frontrunner",
                    "fec_candidate_id": None,
                    "source_url": "https://www.fec.gov/x",
                }
            ]
        )
    )
    assert any("frontrunner" in e for e in errors)


def test_bad_id_fails():
    errors = validate_record(candidate(id="Jane Doe", candidate_ids=["Jane Doe"]))
    assert any("Jane Doe" in e for e in errors)


def test_misplaced_file_flagged(tmp_path: Path):
    rec = vote()
    wrong = tmp_path / "finance" / "jane-doe"
    wrong.mkdir(parents=True)
    path = wrong / "vote-s117-42-jane-doe.json"
    path.write_text(json.dumps(rec), encoding="utf-8")

    report = validate_tree(tmp_path)
    assert path in report
    assert any("misplaced" in e for e in report[path])


def test_valid_tree_is_clean(tmp_path: Path):
    write_record(vote(), tmp_path)
    assert validate_tree(tmp_path) == {}


def test_cli_exit_codes(tmp_path: Path):
    clean = tmp_path / "clean"
    clean.mkdir()
    ok = subprocess.run(
        [sys.executable, "-m", "tracker.validate", str(clean)],
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0

    bad_root = tmp_path / "bad"
    bad = vote(topics=["not-a-topic"])
    write_record(bad, bad_root)
    fail = subprocess.run(
        [sys.executable, "-m", "tracker.validate", str(bad_root)],
        capture_output=True,
        text=True,
    )
    assert fail.returncode == 1
    assert "not-a-topic" in fail.stdout


def test_bad_source_url_fails():
    assert any("source_url" in e for e in validate_record(vote(source_url="not a url at all")))


def test_bad_collected_at_fails():
    assert any("collected_at" in e for e in validate_record(vote(collected_at="yesterday")))


def test_bad_published_at_fails():
    assert any("published_at" in e for e in validate_record(vote(published_at="whenever")))


def test_malformed_topic_reported_not_crash():
    assert validate_record(vote(topics=[{"a": 1}]))


def test_unknown_folder_flagged(tmp_path: Path):
    folder = tmp_path / "mystery-folder" / "jane-doe"
    folder.mkdir(parents=True)
    (folder / "2026.json").write_text("{}", encoding="utf-8")
    report = validate_tree(tmp_path)
    assert any("no schema" in e for errs in report.values() for e in errs)


def test_non_json_file_flagged(tmp_path: Path):
    write_record(vote(), tmp_path)
    (tmp_path / "record" / "jane-doe" / "notes.md").write_text("x", encoding="utf-8")
    report = validate_tree(tmp_path)
    assert any("not a JSON" in e for errs in report.values() for e in errs)

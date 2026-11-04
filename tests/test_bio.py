from tracker.records import record_path
from tracker.tier import classify_paths
from tracker.validate import validate_record, validate_tree


def bio(**overrides):
    rec = {
        "id": "trump-office-president-2017",
        "type": "bio",
        "candidate_ids": ["donald-trump"],
        "source_url": "https://millercenter.org/president/donald-trump",
        "published_at": "2017-01-20",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "manual",
        "topics": [],
        "kind": "office",
        "title": "President of the United States",
        "organization": "United States",
        "start_date": "2017-01-20",
        "end_date": "2021-01-20",
        "location": None,
    }
    rec.update(overrides)
    return rec


def test_valid_office_passes():
    assert validate_record(bio()) == []


def test_all_kinds_accepted():
    for kind in ("office", "education", "career"):
        assert validate_record(bio(kind=kind)) == []


def test_open_ended_entry_allowed():
    assert validate_record(bio(end_date=None)) == []


def test_end_before_start_fails():
    errors = validate_record(bio(start_date="2021-01-20", end_date="2017-01-20"))
    assert any("end_date" in e for e in errors)


def test_unknown_kind_fails():
    assert validate_record(bio(kind="opinion"))


def test_stance_field_rejected():
    assert validate_record(bio(stance="supports X"))


def test_bio_path_is_judgment_tier():
    assert classify_paths(["data/bio/donald-trump/trump-office-president-2017.json"]) == "judgment"


def test_misplaced_bio_flagged(tmp_path):
    rec = bio()
    expected = record_path(rec, tmp_path)
    assert expected == tmp_path / "bio" / "donald-trump" / "trump-office-president-2017.json"
    wrong = tmp_path / "bio" / "elsewhere.json"
    wrong.parent.mkdir(parents=True)
    wrong.write_text('{"x": 1}', encoding="utf-8")
    report = validate_tree(tmp_path)
    assert wrong in report

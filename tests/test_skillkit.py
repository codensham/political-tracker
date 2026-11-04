import pytest

from tracker.records import record_path
from tracker.skillkit import write_checked


def statement(**overrides):
    rec = {
        "id": "statement-jane-doe-guns-2024",
        "type": "statement",
        "candidate_ids": ["jane-doe"],
        "source_url": "https://example.com/speech",
        "published_at": "2024-08-10",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "manual",
        "topics": ["guns"],
        "quote": "We will protect gun rights.",
        "speaker": "Jane Doe",
        "venue": "Rally",
        "context": None,
        "archive_url": None,
    }
    rec.update(overrides)
    return rec


@pytest.mark.parametrize("field", ["stance", "sentiment", "summary", "verdict"])
def test_refuses_stance_fields(field, tmp_path):
    with pytest.raises(ValueError, match=field):
        write_checked(statement(**{field: "supports"}), tmp_path)
    assert not any(tmp_path.rglob("*.json"))


def test_refuses_missing_source_url(tmp_path):
    rec = statement()
    del rec["source_url"]
    with pytest.raises(ValueError, match="source_url"):
        write_checked(rec, tmp_path)


def test_refuses_empty_source_url(tmp_path):
    with pytest.raises(ValueError, match="source_url"):
        write_checked(statement(source_url=""), tmp_path)


def test_refuses_schema_invalid_record(tmp_path):
    with pytest.raises(ValueError):
        write_checked(statement(quote="x" * 281), tmp_path)


def test_accepts_valid_statement_at_its_folder_path(tmp_path):
    rec = statement()
    assert write_checked(rec, tmp_path) is True
    assert record_path(rec, tmp_path).exists()


def test_unchanged_rewrite_reports_no_change(tmp_path):
    write_checked(statement(), tmp_path)
    assert write_checked(statement(), tmp_path) is False

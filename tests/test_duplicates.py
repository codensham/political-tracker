from pathlib import Path

from tracker.records import write_record
from tracker.validate import duplicate_keys, validate_tree


def jane():
    return {
        "id": "jane-doe",
        "type": "candidate",
        "candidate_ids": ["jane-doe"],
        "source_url": "https://www.fec.gov/data/candidate/P00000001/",
        "published_at": "2026-11-03",
        "collected_at": "2026-11-04T00:00:00Z",
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
        "icpsr": None,
        "bioguide_id": None,
        "official_site": None,
        "inclusion_reason": "test fixture",
    }


def statement(rid, quote, url="https://example.com/speech"):
    return {
        "id": rid,
        "type": "statement",
        "candidate_ids": ["jane-doe"],
        "source_url": url,
        "published_at": "2024-08-10",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "manual",
        "topics": [],
        "quote": quote,
        "speaker": "Jane Doe",
        "venue": None,
        "context": None,
        "archive_url": None,
    }


def article(rid, url):
    return {
        "id": rid,
        "type": "article",
        "candidate_ids": ["jane-doe"],
        "source_url": url,
        "published_at": "2024-08-10",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "rss@1.0",
        "topics": [],
        "outlet_id": "npr",
        "headline": "Doe speaks",
        "author": None,
        "archive_url": None,
        "extraction_status": "pending",
    }


def test_same_quote_from_same_source_is_a_duplicate(tmp_path: Path):
    write_record(jane(), tmp_path)
    write_record(statement("statement-a", "We will act."), tmp_path)
    write_record(statement("statement-b", "We will act."), tmp_path)
    report = validate_tree(tmp_path)
    assert len(report) == 2
    assert all(any("duplicate" in e for e in errs) for errs in report.values())


def test_two_different_quotes_from_one_speech_are_not_duplicates(tmp_path: Path):
    write_record(jane(), tmp_path)
    write_record(statement("statement-a", "We will act."), tmp_path)
    write_record(statement("statement-b", "We will not wait."), tmp_path)
    assert validate_tree(tmp_path) == {}


def test_same_article_url_twice_is_a_duplicate(tmp_path: Path):
    write_record(article("article-npr-a", "https://example.com/story"), tmp_path)
    write_record(article("article-npr-b", "https://example.com/story"), tmp_path)
    report = validate_tree(tmp_path)
    assert len(report) == 2


def test_duplicate_keys_are_per_type():
    records = [statement("a", "x"), article("b", "https://example.com/speech")]
    keys = [duplicate_keys(r) for r in records]
    assert keys[0] != keys[1]

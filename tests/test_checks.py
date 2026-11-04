import httpx

from tracker.checks import (
    changed_record_paths,
    check_quote,
    check_records,
    link_status,
    normalize,
    quote_in_source,
)
from tracker.records import write_record
from tracker.validate import validate_record, validate_tree

PAGE = """<html><head><style>.x{}</style></head><body>
<p>We will <b>build</b> the wall—and they will pay.</p>
<p>Thank   you&nbsp;all.</p></body></html>"""


def client(status=200, body=PAGE, raise_exc=None):
    def handler(request):
        if raise_exc:
            raise raise_exc
        return httpx.Response(status, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_normalize_strips_tags_entities_and_dashes():
    assert "we will build the wall-and they will pay." in normalize(PAGE)
    assert "thank you all." in normalize(PAGE)


def test_verbatim_quote_found_across_tags():
    assert quote_in_source("we will build the wall-and they will pay.", PAGE)


def test_altered_quote_not_found():
    assert not quote_in_source("we will build the wall and they will pay for it", PAGE)


def test_check_quote_ok_error_warning():
    assert check_quote(client(), "https://x.example/p", "Thank you all.")[0] == "ok"
    assert check_quote(client(), "https://x.example/p", "Never said this.")[0] == "error"
    assert check_quote(client(status=503), "https://x.example/p", "Thank you all.")[0] == "warning"
    assert (
        check_quote(client(raise_exc=httpx.ConnectTimeout("t")), "https://x.example/p", "x")[0] == "warning"
    )


def test_link_404_is_error_and_403_is_warning():
    assert link_status(client(status=404), "https://x.example/a")[0] == "error"
    assert link_status(client(status=410), "https://x.example/a")[0] == "error"
    assert link_status(client(status=403), "https://x.example/a")[0] == "warning"
    assert link_status(client(status=429), "https://x.example/a")[0] == "warning"
    assert link_status(client(status=200), "https://x.example/a")[0] == "ok"
    assert link_status(client(raise_exc=httpx.ReadTimeout("t")), "https://x.example/a")[0] == "warning"


def statement(**overrides):
    rec = {
        "id": "trump-quote-1",
        "type": "statement",
        "candidate_ids": ["donald-trump"],
        "source_url": "https://x.example/speech",
        "published_at": "2024-07-01",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "manual",
        "topics": ["economy"],
        "quote": "Thank you all.",
        "speaker": "Donald Trump",
        "venue": "Rally",
        "context": None,
        "archive_url": None,
    }
    rec.update(overrides)
    return rec


def test_statement_schema_valid():
    assert validate_record(statement()) == []


def test_statement_quote_length_limit():
    assert validate_record(statement(quote="x" * 281))


def test_check_records_blocks_on_missing_quote_and_dead_link():
    recs = [statement(quote="Never said this.")]
    report = check_records(recs, client())
    assert any("not found verbatim" in e for e in report.errors)


def test_check_records_skips_unchanged_types():
    recs = [{"id": "bio-1", "type": "bio", "source_url": "https://x.example/"}]
    report = check_records(recs, client(status=404))
    assert report.errors == [] and report.warnings == []


def test_changed_record_paths_only_added_or_modified_json():
    lines = [
        "A\tdata/statements/donald-trump/trump-quote-1.json",
        "M\tdata/articles/donald-trump/a.json",
        "D\tdata/articles/donald-trump/old.json",
        "A\tsrc/tracker/checks.py",
    ]
    assert changed_record_paths(lines) == [
        "data/statements/donald-trump/trump-quote-1.json",
        "data/articles/donald-trump/a.json",
    ]


def test_speaker_must_be_candidate_name_or_alias(tmp_path):
    write_record(
        {
            "id": "donald-trump",
            "type": "candidate",
            "candidate_ids": ["donald-trump"],
            "source_url": "https://www.fec.gov/",
            "published_at": "2026-11-04",
            "collected_at": "2026-11-04T00:00:00Z",
            "collector": "candidates@1.0",
            "topics": [],
            "name": "Donald J. Trump",
            "aliases": ["Donald Trump"],
            "candidacies": [
                {
                    "office": "president",
                    "year": 2024,
                    "party": "REP",
                    "result": "won",
                    "fec_candidate_id": "P80001571",
                    "source_url": "https://www.fec.gov/",
                }
            ],
            "fec_candidate_ids": ["P80001571"],
            "icpsr": None,
            "bioguide_id": None,
            "official_site": None,
            "inclusion_reason": "test",
        },
        tmp_path,
    )
    write_record(statement(speaker="Donald Trump"), tmp_path)
    write_record(statement(id="trump-quote-2", speaker="Someone Else"), tmp_path)
    report = validate_tree(tmp_path)
    assert len(report) == 1
    (errors,) = report.values()
    assert any("speaker" in e for e in errors)

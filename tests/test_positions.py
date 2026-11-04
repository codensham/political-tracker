import pytest

from tracker.positions import KeyQuoteNotFound, build_position, content_hash
from tracker.validate import validate_record

PAGE_V1 = "<html><body><h1>Our plan</h1><p>We will  cut   taxes for working families.</p></body></html>"
PAGE_V2 = "<html><body><h1>Our plan</h1><p>We will cut taxes for working families and small business.</p></body></html>"


def test_hash_ignores_markup_and_whitespace():
    assert content_hash(PAGE_V1) == content_hash("Our plan\n\nWe will cut   taxes for working families.")


def test_first_capture_is_not_changed():
    rec = build_position("donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-04")
    assert rec["changed"] is False
    assert (
        validate_record({**rec, "collected_at": "2026-11-04T00:00:00Z", "collector": "positions@1.0"}) == []
    )


def test_changed_text_sets_changed_flag():
    prev = content_hash(PAGE_V1)
    rec = build_position(
        "donald-trump", "https://example.com/plan", PAGE_V2, "2026-11-05", previous_hash=prev
    )
    assert rec["changed"] is True


def test_unchanged_text_clears_flag():
    prev = content_hash(PAGE_V1)
    rec = build_position(
        "donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-05", previous_hash=prev
    )
    assert rec["changed"] is False


def test_no_page_text_is_stored():
    rec = build_position("donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-04")
    assert "working families" not in str(rec)


def test_key_quote_must_appear_verbatim():
    rec = build_position(
        "donald-trump",
        "https://example.com/plan",
        PAGE_V1,
        "2026-11-04",
        key_quotes=["cut taxes for working families"],
    )
    assert rec["key_quotes"] == ["cut taxes for working families"]
    with pytest.raises(KeyQuoteNotFound):
        build_position(
            "donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-04", key_quotes=["abolish taxes"]
        )


def test_at_most_five_key_quotes_in_schema():
    rec = build_position("donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-04")
    rec["key_quotes"] = ["cut taxes"] * 6
    assert validate_record({**rec, "collected_at": "2026-11-04T00:00:00Z", "collector": "positions@1.0"})


def test_record_id_is_stable_per_capture():
    a = build_position("donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-04")
    b = build_position("donald-trump", "https://example.com/plan", PAGE_V1, "2026-11-04")
    assert a["id"] == b["id"]

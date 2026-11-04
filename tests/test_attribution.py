import pytest

from tracker.validate import validate_record

META = {
    "candidate_ids": ["donald-trump"],
    "collected_at": "2026-11-04T00:00:00Z",
    "collector": "manual",
    "topics": [],
}


def endorsement(**overrides):
    rec = {
        "id": "endorsement-trump-smith-2024",
        "type": "endorsement",
        "source_url": "https://example.com/endorsement",
        "published_at": "2024-03-01",
        "endorser": "Jane Smith",
        "endorser_type": "elected_official",
        "date": "2024-03-01",
        **META,
    }
    rec.update(overrides)
    return rec


def appearance(**overrides):
    rec = {
        "id": "appearance-trump-debate-2024",
        "type": "appearance",
        "source_url": "https://example.com/debate",
        "published_at": "2024-09-10",
        "event": "Presidential debate",
        "venue": "National Constitution Center",
        "host": "ABC News",
        "date": "2024-09-10",
        "transcript_url": None,
        "video_url": None,
        **META,
    }
    rec.update(overrides)
    return rec


def poll(**overrides):
    rec = {
        "id": "poll-trump-ap-2024-10",
        "type": "poll",
        "source_url": "https://example.com/poll",
        "published_at": "2024-10-20",
        "pollster": "Example Polling Co.",
        "value": 47.0,
        "field_start": "2024-10-14",
        "field_end": "2024-10-18",
        "sample": 1200,
        "population": "registered voters",
        **META,
    }
    rec.update(overrides)
    return rec


@pytest.mark.parametrize("make", [endorsement, appearance, poll])
def test_fixture_validates(make):
    assert validate_record(make()) == []


def test_missing_pollster_fails():
    rec = poll()
    del rec["pollster"]
    assert validate_record(rec)


def test_empty_pollster_fails():
    assert validate_record(poll(pollster=""))


def test_empty_endorser_fails():
    assert validate_record(endorsement(endorser=""))


@pytest.mark.parametrize("make", [endorsement, appearance, poll])
def test_stance_field_rejected(make):
    assert validate_record({**make(), "stance": "supports"})
    assert validate_record({**make(), "sentiment": "positive"})


def test_poll_end_before_start_fails():
    assert validate_record(poll(field_start="2024-10-18", field_end="2024-10-14"))


def test_poll_value_must_be_a_percentage():
    assert validate_record(poll(value=120))


def test_types_are_registered_with_folders():
    from tracker.records import TYPE_DIRS

    assert TYPE_DIRS["endorsement"] == "endorsements"
    assert TYPE_DIRS["appearance"] == "appearances"
    assert TYPE_DIRS["poll"] == "polls"

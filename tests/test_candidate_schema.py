from tracker.validate import validate_record


def candidacy(**overrides):
    c = {
        "office": "president",
        "year": 2024,
        "party": "REP",
        "result": "won",
        "fec_candidate_id": "P80001571",
        "source_url": "https://www.fec.gov/data/candidate/P80001571/",
    }
    c.update(overrides)
    return c


def candidate(**overrides):
    rec = {
        "id": "donald-trump",
        "type": "candidate",
        "candidate_ids": ["donald-trump"],
        "source_url": "https://www.fec.gov/data/candidate/P80001571/",
        "published_at": "2026-11-04",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "candidates@1.0",
        "topics": [],
        "name": "Donald J. Trump",
        "aliases": ["Donald Trump", "Donald J. Trump"],
        "candidacies": [candidacy()],
        "fec_candidate_ids": ["P80001571"],
        "icpsr": None,
        "bioguide_id": None,
        "official_site": None,
        "inclusion_reason": "past candidate",
    }
    rec.update(overrides)
    return rec


def test_valid_candidate_passes():
    assert validate_record(candidate()) == []


def test_all_result_values_accepted():
    for result in ["potential", "declared", "withdrew", "nominee", "won", "lost"]:
        assert validate_record(candidate(candidacies=[candidacy(result=result)])) == []


def test_unknown_result_fails():
    errors = validate_record(candidate(candidacies=[candidacy(result="frontrunner")]))
    assert any("result" in e for e in errors)


def test_office_must_be_president():
    errors = validate_record(candidate(candidacies=[candidacy(office="senate")]))
    assert errors


def test_candidacy_needs_a_source_url():
    bad = candidacy()
    del bad["source_url"]
    assert validate_record(candidate(candidacies=[bad]))


def test_candidacy_fec_id_may_be_null():
    assert validate_record(candidate(candidacies=[candidacy(fec_candidate_id=None)])) == []


def test_at_least_one_candidacy_required():
    assert validate_record(candidate(candidacies=[]))


def test_aliases_required():
    bad = candidate()
    del bad["aliases"]
    assert validate_record(bad)


def test_empty_aliases_fail():
    assert validate_record(candidate(aliases=[]))


def test_top_level_status_rejected():
    errors = validate_record(candidate(status="nominee"))
    assert errors


def test_top_level_party_rejected():
    errors = validate_record(candidate(party="REP"))
    assert errors


def test_social_accounts_optional_and_checked():
    ok = [{"platform": "x", "handle": "example", "url": "https://x.com/example"}]
    assert validate_record(candidate(social_accounts=ok)) == []
    bad = [{"platform": "x", "handle": "example"}]
    assert validate_record(candidate(social_accounts=bad))


def test_real_trump_record_has_three_candidacies():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "data" / "candidates" / "donald-trump.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert [(c["year"], c["result"]) for c in rec["candidacies"]] == [
        (2016, "won"),
        (2020, "lost"),
        (2024, "won"),
    ]
    assert validate_record(rec) == []

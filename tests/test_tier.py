from tracker.tier import classify_paths


def test_official_paths():
    assert classify_paths([
        "data/finance/jane-doe/finance-jane-doe-p00000001-2028.json",
        "data/record/jane-doe/vote-s117-1-jane-doe.json",
        "data/disclosures/jane-doe/2026.json",
    ]) == "official"


def test_mixed_is_judgment():
    assert classify_paths([
        "data/finance/jane-doe/finance-jane-doe-p00000001-2028.json",
        "data/candidates/x.json",
    ]) == "judgment"


def test_code_change_is_judgment():
    assert classify_paths(["src/tracker/tier.py"]) == "judgment"


def test_empty_is_judgment():
    assert classify_paths([]) == "judgment"
    assert classify_paths(["", "  "]) == "judgment"

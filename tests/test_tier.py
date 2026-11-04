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


from tracker.tier import classify_name_status


def test_deletion_is_judgment():
    assert classify_name_status(["D\tdata/record/jane-doe/v.json"]) == "judgment"


def test_added_and_modified_official_is_official():
    assert classify_name_status([
        "A\tdata/record/jane-doe/v.json",
        "M\tdata/finance/jane-doe/f.json",
    ]) == "official"


def test_rename_is_judgment():
    assert classify_name_status(["R100\tdocs/a.md\tdata/record/x/n.md"]) == "judgment"


def test_empty_name_status_is_judgment():
    assert classify_name_status([]) == "judgment"


def test_executive_actions_are_official():
    assert classify_paths([
        "data/executive-actions/donald-trump/exec-2017-01799.json",
    ]) == "official"

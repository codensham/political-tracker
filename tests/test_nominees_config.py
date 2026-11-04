from pathlib import Path

from tracker.candidates import load_config

CONFIG = Path(__file__).resolve().parents[1] / "config" / "candidates.yaml"

EXPECTED = {
    "al-gore": [(2000, "lost")],
    "george-w-bush": [(2000, "won"), (2004, "won")],
    "john-kerry": [(2004, "lost")],
    "barack-obama": [(2008, "won"), (2012, "won")],
    "john-mccain": [(2008, "lost")],
    "mitt-romney": [(2012, "lost")],
    "hillary-clinton": [(2016, "lost")],
    "donald-trump": [(2016, "won"), (2020, "lost"), (2024, "won")],
    "joe-biden": [(2020, "won"), (2024, "withdrew")],
    "kamala-harris": [(2024, "lost")],
}


def test_config_has_exactly_the_scoped_nominees():
    ids = {c["id"] for c in load_config(CONFIG)}
    assert ids == set(EXPECTED)


def test_candidacies_match_scope():
    by_id = {c["id"]: c for c in load_config(CONFIG)}
    for cid, expected in EXPECTED.items():
        got = [(k["year"], k["result"]) for k in by_id[cid]["candidacies"]]
        assert got == expected, cid


def test_every_candidacy_has_an_fec_id_and_source():
    for entry in load_config(CONFIG):
        for k in entry["candidacies"]:
            assert k["fec_candidate_id"], entry["id"]
            assert k["source_url"].startswith("https://www.fec.gov/"), entry["id"]


def test_no_bare_surname_aliases():
    for entry in load_config(CONFIG):
        assert all(len(alias.split()) >= 2 for alias in entry["aliases"]), entry["id"]

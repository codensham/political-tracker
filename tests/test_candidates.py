import json
from pathlib import Path

import pytest

from tracker.candidates import sync_candidates
from tracker.records import record_path
from tracker.validate import validate_tree

CONFIG = """
candidates:
  - id: jane-doe
    name: Jane Doe
    aliases: ["Jane Doe"]
    candidacies:
      - {office: president, year: 2028, party: DEM, result: potential, fec_candidate_id: P00000001, source_url: "https://www.fec.gov/data/candidate/P00000001/"}
    as_of: "2026-11-03"
    fec_candidate_ids: ["P00000001"]
    icpsr: 12345
    bioguide_id: null
    official_site: https://janedoe.example/
    inclusion_reason: "FEC Form 2 filed for 2028 (fec.gov)"
  - id: john-roe
    name: John Roe
    aliases: ["John Roe"]
    candidacies:
      - {office: president, year: 2028, party: REP, result: potential, fec_candidate_id: P00000002, source_url: "https://www.fec.gov/data/candidate/P00000002/"}
    as_of: "2026-11-03"
    fec_candidate_ids: ["P00000002"]
    icpsr: null
    bioguide_id: null
    official_site: null
    inclusion_reason: "Polling 2%+ in two named national polls"
"""


def write_config(tmp_path: Path, text: str = CONFIG) -> Path:
    path = tmp_path / "candidates.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_sync_writes_valid_records(tmp_path: Path):
    config = write_config(tmp_path)
    data = tmp_path / "data"

    assert sync_candidates(config, data) == 2

    for cid in ("jane-doe", "john-roe"):
        assert (data / "candidates" / f"{cid}.json").exists()
    assert validate_tree(data) == {}

    jane = json.loads((data / "candidates" / "jane-doe.json").read_text(encoding="utf-8"))
    assert jane["source_url"] == "https://janedoe.example/"
    assert jane["collector"] == "candidates@1.0"
    assert record_path(jane, data) == data / "candidates" / "jane-doe.json"

    roe = json.loads((data / "candidates" / "john-roe.json").read_text(encoding="utf-8"))
    assert roe["source_url"] == "https://www.fec.gov/data/candidate/P00000002/"


def test_sync_idempotent(tmp_path: Path):
    config = write_config(tmp_path)
    data = tmp_path / "data"
    sync_candidates(config, data)
    assert sync_candidates(config, data) == 0


def test_retired_status_key_rejected(tmp_path: Path):
    old = CONFIG.replace("candidacies:", "status: potential\n    candidacies:", 1)
    config = write_config(tmp_path, old)
    with pytest.raises(ValueError, match="'status' is retired"):
        sync_candidates(config, tmp_path / "data")


def test_duplicate_id_rejected(tmp_path: Path):
    dup = CONFIG.replace("id: john-roe", "id: jane-doe")
    config = write_config(tmp_path, dup)
    with pytest.raises(ValueError, match="duplicate"):
        sync_candidates(config, tmp_path / "data")

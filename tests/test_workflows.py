from pathlib import Path

import yaml

WF_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def load(name: str) -> dict:
    return yaml.safe_load((WF_DIR / name).read_text(encoding="utf-8"))


def triggers(doc: dict) -> dict:
    # PyYAML reads the bare key `on` as boolean True.
    return doc.get("on", doc.get(True))


def test_ci_runs_when_label_added():
    types = triggers(load("ci.yml"))["pull_request"]["types"]
    assert "labeled" in types


def test_top_level_permissions_read_only():
    assert load("ci.yml")["permissions"] == {"contents": "read"}


def test_tier_job_can_enable_and_disable_auto_merge():
    perms = load("ci.yml")["jobs"]["tier"]["permissions"]
    assert perms["contents"] == "write"
    assert perms["pull-requests"] == "write"


def test_tier_classifies_without_renames_and_disables_auto_merge():
    text = (WF_DIR / "ci.yml").read_text(encoding="utf-8")
    assert "--name-status" in text and "--no-renames" in text
    assert "--disable-auto" in text


def test_collect_official_runs_house_clerk():
    steps = load("collect-official.yml")["jobs"]["collect"]["steps"]
    runs = "\n".join(s.get("run", "") for s in steps)
    assert "python -m tracker.collectors house_clerk" in runs

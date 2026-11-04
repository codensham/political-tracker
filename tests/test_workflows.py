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


def test_ci_runs_ruff_check_and_format():
    runs = "\n".join(s.get("run", "") for s in load("ci.yml")["jobs"]["test"]["steps"])
    assert "ruff check" in runs
    assert "ruff format --check" in runs


def test_collect_official_runs_every_collector_and_fails_at_the_end():
    steps = load("collect-official.yml")["jobs"]["collect"]["steps"]
    run_step = next(s for s in steps if s.get("name") == "Run official collectors")
    assert "failures" in run_step["run"]
    assert "|| " in run_step["run"]  # a failed collector is recorded, not fatal, mid-run
    final = [s for s in steps if s.get("name") == "Fail if any collector failed"]
    assert final and "exit 1" in final[0]["run"]


def test_collect_articles_runs_rss_daily_on_its_own_branch():
    doc = load("collect-articles.yml")
    assert "schedule" in triggers(doc)
    text = (WF_DIR / "collect-articles.yml").read_text(encoding="utf-8")
    assert "python -m tracker.collectors rss" in text
    assert "branch: collect/articles" in text
    assert "BOT_TOKEN" in text

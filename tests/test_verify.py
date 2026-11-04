import importlib.util
import sys
from pathlib import Path

import pytest

VERIFY_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify.py"


@pytest.fixture
def verify():
    spec = importlib.util.spec_from_file_location("verify_script", VERIFY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ok():
    return [sys.executable, "-c", "pass"]


def fail():
    return [sys.executable, "-c", "import sys; sys.exit(3)"]


def test_all_pass_returns_zero(verify, capsys):
    assert verify.run_steps([("a", ok()), ("b", ok())]) == 0
    assert "verify OK" in capsys.readouterr().out


def test_first_failure_stops_and_names_step(verify, capsys):
    steps = [("a", ok()), ("broken", fail()), ("never", ok())]
    assert verify.run_steps(steps) == 3
    out = capsys.readouterr().out
    assert "verify FAILED at: broken" in out
    assert "never" not in out


def test_steps_cover_lint_format_tests_validate(verify):
    names = [name for name, _ in verify.STEPS]
    assert names == ["lint", "format", "tests", "validate data"]

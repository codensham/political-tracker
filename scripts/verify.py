"""Run every check the project requires. Exit 0 only if all pass.

Usage: python scripts/verify.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STEPS: list[tuple[str, list[str]]] = [
    ("lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("tests", [sys.executable, "-m", "pytest", "-q"]),
    ("validate data", [sys.executable, "-m", "tracker.validate", "data"]),
]


def run_steps(steps: list[tuple[str, list[str]]]) -> int:
    """Run steps in order, stop at the first failure, return its exit code (0 if all pass)."""
    for name, argv in steps:
        print(f"== {name}", flush=True)
        result = subprocess.run(argv, cwd=REPO_ROOT)
        if result.returncode != 0:
            print(f"verify FAILED at: {name} (exit {result.returncode})", flush=True)
            return result.returncode
    print("verify OK", flush=True)
    return 0


def main() -> int:
    return run_steps(STEPS)


if __name__ == "__main__":
    sys.exit(main())

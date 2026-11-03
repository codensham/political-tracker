"""Decide whether a set of changed paths is official-record data (auto-mergeable) or needs review."""

from __future__ import annotations

import sys
from typing import Literal

OFFICIAL_PREFIXES = ("data/finance/", "data/record/", "data/disclosures/")


def classify_paths(paths: list[str]) -> Literal["official", "judgment"]:
    cleaned = [p.strip().replace("\\", "/") for p in paths if p.strip()]
    if cleaned and all(p.startswith(OFFICIAL_PREFIXES) for p in cleaned):
        return "official"
    return "judgment"


def main() -> int:
    print(classify_paths(sys.stdin.read().splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

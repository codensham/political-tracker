"""Decide whether a set of changed paths is official-record data (auto-mergeable) or needs review."""

from __future__ import annotations

import sys
from typing import Literal

OFFICIAL_PREFIXES = (
    "data/finance/",
    "data/record/",
    "data/disclosures/",
    "data/executive-actions/",
)


def classify_paths(paths: list[str]) -> Literal["official", "judgment"]:
    cleaned = [p.strip().replace("\\", "/") for p in paths if p.strip()]
    if cleaned and all(p.startswith(OFFICIAL_PREFIXES) for p in cleaned):
        return "official"
    return "judgment"


def classify_name_status(lines: list[str]) -> Literal["official", "judgment"]:
    """Classify `git diff --name-status --no-renames` output.

    Only additions and modifications under official folders are official. A deletion,
    rename, copy or type change always needs review.
    """
    paths: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        fields = line.split("\t")
        status, path = fields[0], fields[-1]
        if status[:1] not in ("A", "M"):
            return "judgment"
        paths.append(path)
    return classify_paths(paths)


def main() -> int:
    print(classify_name_status(sys.stdin.read().splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Policy-area crosswalk: Congress.gov policy area name -> our topic ids (D-020)."""

from __future__ import annotations

import json
from functools import lru_cache

from tracker.validate import REPO_ROOT

CROSSWALK_PATH = REPO_ROOT / "taxonomy" / "policy_area_crosswalk.json"


@lru_cache(maxsize=1)
def load_crosswalk() -> dict[str, list[str]]:
    """Map each listed policy area to its topic ids. Unlisted areas are not in the mapping."""
    data = json.loads(CROSSWALK_PATH.read_text(encoding="utf-8"))
    return {m["policy_area"]: list(m["topics"]) for m in data["mappings"]}


def topics_for(policy_area: str | None) -> list[str]:
    if not policy_area:
        return []
    return list(load_crosswalk().get(policy_area, []))

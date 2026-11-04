"""Read API keys from the environment, falling back to a git-ignored .env at the repo root.

Blank values count as unset. Key values are never printed or logged.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(root: Path | None = None) -> dict[str, str]:
    """Parse KEY=value lines from <root>/.env. Missing file gives {}. Blank values are dropped."""
    path = Path(root or REPO_ROOT) / ".env"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if key.strip() and value:
            values[key.strip()] = value
    return values


def get_key(name: str, root: Path | None = None) -> str | None:
    """Environment variable first, then .env. Returns None when unset or blank."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    return load_dotenv(root).get(name) or None

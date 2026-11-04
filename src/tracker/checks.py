"""Link and quote checks for changed records (spec §6, D-024).

- link: 404 or 410 is an error that blocks the PR. 401, 403, 429, 5xx, redirects that fail and
  timeouts are warnings (paywalls and rate limits are not the record's fault).
- quote: a statement's quote must appear verbatim in its source after HTML tags are removed and
  whitespace and common typography are normalized. If the source cannot be fetched, it is a warning.

Run as: python -m tracker.checks --changed [--base origin/main] [--data data]
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from tracker.records import load_records

BLOCKING_STATUS = {404, 410}
USER_AGENT = "political-tracker (+https://github.com/codensham/political-tracker)"
CHECKED_TYPES = {"article", "statement"}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def link_status(client: httpx.Client, url: str) -> tuple[str, str]:
    """Return ('ok' | 'error' | 'warning', detail) for a source URL."""
    try:
        resp = client.get(url, follow_redirects=True, timeout=30)
    except httpx.HTTPError as exc:
        return "warning", f"unreachable: {type(exc).__name__}"
    if resp.status_code in BLOCKING_STATUS:
        return "error", f"HTTP {resp.status_code}"
    if resp.status_code >= 400:
        return "warning", f"HTTP {resp.status_code}"
    return "ok", f"HTTP {resp.status_code}"


def normalize(text: str) -> str:
    """Strip tags, decode entities, fold typography and collapse whitespace."""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.translate(
        str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})
    )
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_in_source(quote: str, source_html: str) -> bool:
    return normalize(quote) in normalize(source_html)


def check_quote(client: httpx.Client, url: str, quote: str) -> tuple[str, str]:
    try:
        resp = client.get(url, follow_redirects=True, timeout=30)
    except httpx.HTTPError as exc:
        return "warning", f"source unreachable: {type(exc).__name__}"
    if resp.status_code >= 400:
        return "warning", f"source HTTP {resp.status_code}"
    if quote_in_source(quote, resp.text):
        return "ok", "verbatim"
    return "error", "quote not found verbatim in source"


def changed_record_paths(name_status_lines: list[str]) -> list[str]:
    """Paths of added or modified JSON records from `git diff --name-status`."""
    paths = []
    for line in name_status_lines:
        if not line.strip():
            continue
        fields = line.split("\t")
        status, path = fields[0], fields[-1]
        if status[:1] in ("A", "M") and path.endswith(".json"):
            paths.append(path.replace("\\", "/"))
    return paths


def check_records(records: list[dict], client: httpx.Client) -> Report:
    report = Report()
    for rec in records:
        if rec.get("type") not in CHECKED_TYPES:
            continue
        rid = rec["id"]
        status, detail = link_status(client, rec["source_url"])
        if status == "error":
            report.errors.append(f"{rid}: source link {detail}")
        elif status == "warning":
            report.warnings.append(f"{rid}: source link {detail}")
        if rec["type"] == "statement":
            qstatus, qdetail = check_quote(client, rec["source_url"], rec["quote"])
            if qstatus == "error":
                report.errors.append(f"{rid}: {qdetail}")
            elif qstatus == "warning":
                report.warnings.append(f"{rid}: {qdetail}")
    return report


def _git_changed(base: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-status", "--no-renames", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return changed_record_paths(out.splitlines())


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="tracker.checks")
    parser.add_argument("--changed", action="store_true", help="check only records changed vs base")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--data", default="data")
    args = parser.parse_args(argv)

    data = Path(args.data)
    records = list(load_records(data))
    if args.changed:
        changed = set(_git_changed(args.base))
        records = [r for r in records if any(p.endswith(f"/{r['id']}.json") for p in changed)]

    client = httpx.Client(headers={"User-Agent": USER_AGENT})
    report = check_records(records, client)
    for w in report.warnings:
        print(f"WARN  {w}")
    for e in report.errors:
        print(f"ERROR {e}")
    print(
        f"checked {len(records)} record(s): {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    )
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())

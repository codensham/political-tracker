"""MCP tools. Every result carries source_url on each record; the server adds no characterization."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from tracker.mcp_server.index import DataIndex, UnknownCandidate
from tracker.validate import REPO_ROOT

NOTE = "Records are sourced evidence; see source_url on each. This server does not characterize positions."

mcp = FastMCP("political-tracker")
_index: DataIndex | None = None


def configure(root: Path) -> None:
    global _index
    _index = DataIndex.load(Path(root))


def _idx() -> DataIndex:
    if _index is None:
        configure(REPO_ROOT / "data")
    return _index


def _ok(records: list[dict], total: int | None = None, limit: int | None = None) -> dict:
    count = len(records) if total is None else total
    truncated = limit is not None and count > limit
    return {"results": records, "count": count, "truncated": truncated, "note": NOTE}


def _valid_date(value: str | None) -> bool:
    if value is None:
        return True
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return len(value) == 10


def _error(exc: Exception) -> dict:
    return {"error": str(exc)}


@mcp.tool()
def list_candidates(status: str | None = None) -> dict:
    """List tracked candidates, optionally filtered by status (potential, declared, withdrawn, nominee).
    Cite source_url for any fact you report about a candidate."""
    return _ok(_idx().candidates(status))


@mcp.tool()
def get_candidate(candidate: str) -> dict:
    """Get one candidate's record (name, party, status, IDs). Cite source_url.
    Unknown ids return an error that lists the valid ids."""
    try:
        return _ok([_idx().candidate(candidate)])
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def search_evidence(
    candidate: str,
    topic: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    types: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """Sourced evidence for a candidate (for example roll-call votes), oldest first.
    Dates are YYYY-MM-DD. Cite source_url for every claim. Do not infer a stance beyond these records."""
    if not (_valid_date(date_from) and _valid_date(date_to)):
        return _error(ValueError("dates must be YYYY-MM-DD, for example 2021-06-01"))
    try:
        recs = _idx().evidence(candidate, topic=topic, date_from=date_from, date_to=date_to, types=types)
    except UnknownCandidate as exc:
        return _error(exc)
    return _ok(recs[:limit], total=len(recs), limit=limit)


@mcp.tool()
def position_timeline(candidate: str, topic: str) -> dict:
    """Evidence for one candidate on one topic, oldest first, so changes over time are visible.
    Present the dated records as they are. Do not declare that a position changed."""
    try:
        return _ok(_idx().evidence(candidate, topic=topic))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_finance(candidate: str, cycle: int | None = None) -> dict:
    """FEC finance totals for a candidate, optionally for one election cycle. Cite source_url."""
    try:
        return _ok(_idx().finance(candidate, cycle=cycle))
    except UnknownCandidate as exc:
        return _error(exc)

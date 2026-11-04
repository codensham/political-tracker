"""MCP tools. Every result carries source_url on each record; the server adds no characterization."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from tracker.mcp_server.index import DataIndex, UnknownCandidate
from tracker.validate import REPO_ROOT

NOTE = "Records are sourced evidence; see source_url on each. This server does not characterize positions."

PERIOD_RE = re.compile(r"\d{4}(-(0[1-9]|1[0-2]))?")

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
def list_candidates(
    office: str | None = None,
    year: int | None = None,
    result: str | None = None,
) -> dict:
    """List tracked candidates with a candidacy matching the filters. office: president.
    result: potential, declared, withdrew, nominee, won, lost. Cite source_url for any fact you report."""
    return _ok(_idx().candidates(office=office, year=year, result=result))


@mcp.tool()
def get_candidate(candidate: str) -> dict:
    """Get one candidate's record (name, aliases, candidacies, IDs). Cite source_url.
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
    """Sourced evidence for a candidate (statements, positions, votes, bills, executive actions,
    articles, endorsements, appearances, polls), oldest first. Dates are YYYY-MM-DD.
    Cite source_url for every claim. Do not infer a stance beyond these records."""
    if not (_valid_date(date_from) and _valid_date(date_to)):
        return _error(ValueError("dates must be YYYY-MM-DD, for example 2021-06-01"))
    try:
        recs = _idx().evidence(candidate, topic=topic, date_from=date_from, date_to=date_to, types=types)
    except UnknownCandidate as exc:
        return _error(exc)
    return _ok(recs[:limit], total=len(recs), limit=limit)


@mcp.tool()
def position_timeline(candidate: str, topic: str) -> dict:
    """Evidence for one candidate on one topic (statements, positions, votes, bills, executive
    actions), oldest first, so changes over time are visible. Present the dated records as they are.
    Do not declare that a position changed."""
    try:
        return _ok(_idx().position_timeline(candidate, topic))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_finance(candidate: str, cycle: int | None = None) -> dict:
    """FEC finance totals for a candidate, optionally for one election cycle. Cite source_url."""
    try:
        return _ok(_idx().finance(candidate, cycle=cycle))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_outside_spending(candidate: str, cycle: int | None = None) -> dict:
    """Independent expenditures for or against a candidate (FEC Schedule E), per committee per
    cycle. Optionally filter by cycle. Cite source_url."""
    try:
        return _ok(_idx().outside_spending(candidate, cycle=cycle))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_bio(candidate: str) -> dict:
    """Offices, education and career entries for a candidate, earliest first. Cite source_url."""
    try:
        return _ok(_idx().bio(candidate))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_disclosures(candidate: str) -> dict:
    """House financial disclosure filings for a candidate, oldest first. Cite source_url."""
    try:
        return _ok(_idx().disclosures(candidate))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_endorsements(candidate: str) -> dict:
    """Endorsements of a candidate, naming each endorser as the source states it, oldest first.
    Cite source_url."""
    try:
        return _ok(_idx().endorsements(candidate))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_appearances(candidate: str) -> dict:
    """Public appearances by a candidate, oldest first. Cite source_url."""
    try:
        return _ok(_idx().appearances(candidate))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def get_polls(candidate: str) -> dict:
    """Polls that include a candidate, attributed to the named pollster, oldest field period first.
    Cite source_url."""
    try:
        return _ok(_idx().polls(candidate))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def media_attention(
    candidate: str | None = None,
    outlet: str | None = None,
    period: str | None = None,
) -> dict:
    """Article counts per candidate and outlet, computed on each call from the article records.
    period: YYYY or YYYY-MM. Each row lists article_ids so counts can be checked."""
    if period is not None and not PERIOD_RE.fullmatch(period):
        return _error(ValueError("period must be YYYY or YYYY-MM, for example 2024 or 2024-10"))
    try:
        return _ok(_idx().media_attention(candidate_id=candidate, outlet_id=outlet, period=period))
    except UnknownCandidate as exc:
        return _error(exc)


@mcp.tool()
def compare(candidates: list[str], topic: str) -> dict:
    """Side-by-side evidence on one topic for several candidates, in the order given. Nothing is
    ranked. Unknown ids return an error that lists the valid ids. Cite source_url for every record."""
    if not candidates:
        return _error(ValueError("name at least one candidate id"))
    try:
        groups = _idx().compare(candidates, topic)
    except UnknownCandidate as exc:
        return _error(exc)
    return _ok(groups)

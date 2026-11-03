import asyncio

from tracker.mcp_server import server

TOOLS = {"list_candidates", "get_candidate", "search_evidence", "position_timeline", "get_finance"}


def test_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == TOOLS


def test_tool_result_shape(seeded_root):
    server.configure(seeded_root)
    result = server.search_evidence("jane-doe")
    assert set(result) == {"results", "count", "note"}
    assert result["count"] == len(result["results"]) == 3
    assert all(r["source_url"] for r in result["results"])
    assert "does not characterize positions" in result["note"]


def test_unknown_candidate_tool_returns_error(seeded_root):
    server.configure(seeded_root)
    result = server.get_candidate("nobody")
    assert "error" in result
    assert "jane-doe" in result["error"]


def test_position_timeline_filters_topic(seeded_root):
    server.configure(seeded_root)
    result = server.position_timeline("john-roe", "guns")
    assert [r["id"] for r in result["results"]] == ["vote-s117-1-john-roe"]


def test_get_finance(seeded_root):
    server.configure(seeded_root)
    result = server.get_finance("jane-doe", cycle=2028)
    assert result["count"] == 1

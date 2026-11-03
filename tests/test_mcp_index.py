import pytest

from tracker.mcp_server.index import DataIndex, UnknownCandidate


def test_evidence_sorted_and_filtered(seeded_root):
    idx = DataIndex.load(seeded_root)
    recs = idx.evidence("jane-doe", date_from="2021-01-01", date_to="2021-12-31")
    assert [r["published_at"] for r in recs] == ["2021-01-05", "2021-06-01"]
    assert all(r["type"] == "vote" for r in idx.evidence("jane-doe"))


def test_topic_filter(seeded_root):
    idx = DataIndex.load(seeded_root)
    recs = idx.evidence("jane-doe", topic="guns")
    assert [r["id"] for r in recs] == ["vote-s117-2-jane-doe"]


def test_unknown_candidate_lists_ids(seeded_root):
    idx = DataIndex.load(seeded_root)
    with pytest.raises(UnknownCandidate) as info:
        idx.candidate("nobody")
    assert "jane-doe" in str(info.value)
    assert "john-roe" in str(info.value)


def test_candidates_status_filter(seeded_root):
    idx = DataIndex.load(seeded_root)
    assert [c["id"] for c in idx.candidates(status="declared")] == ["john-roe"]


def test_finance_cycle_filter(seeded_root):
    idx = DataIndex.load(seeded_root)
    assert [r["cycle"] for r in idx.finance("jane-doe", cycle=2028)] == [2028]
    assert idx.finance("jane-doe", cycle=2026) == []

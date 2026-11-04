import asyncio

import pytest

from tracker.mcp_server import server
from tracker.records import write_record

HASH = "a" * 64

SPEC_TOOLS = {
    "list_candidates",
    "get_candidate",
    "search_evidence",
    "position_timeline",
    "get_finance",
    "get_outside_spending",
    "get_bio",
    "get_disclosures",
    "get_endorsements",
    "get_appearances",
    "get_polls",
    "media_attention",
    "compare",
}


def make(type_, rid, cids, published, topics=(), **fields):
    return {
        "id": rid,
        "type": type_,
        "candidate_ids": cids,
        "source_url": f"https://example.com/{rid}",
        "published_at": published,
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "manual",
        "topics": list(topics),
        **fields,
    }


EXTRA = [
    make(
        "bio",
        "bio-jane-doe-2015",
        ["jane-doe"],
        "2015-01-01",
        kind="office",
        title="Senator",
        organization="U.S. Senate",
        start_date="2015-01-03",
        end_date=None,
        location=None,
    ),
    make(
        "bio",
        "bio-jane-doe-2005",
        ["jane-doe"],
        "2005-01-01",
        kind="career",
        title="Lawyer",
        organization="Doe & Co",
        start_date="2005-06-01",
        end_date="2014-12-31",
        location="New York",
    ),
    make(
        "outside_spending",
        "outside-jane-doe-2024-c00000001-s",
        ["jane-doe"],
        "2024-12-31",
        cycle=2024,
        support_oppose="support",
        amount=1000.0,
        committee_id="C00000001",
        committee_name="PAC One",
        fec_candidate_id="P00000001",
    ),
    make(
        "outside_spending",
        "outside-jane-doe-2022-c00000001-o",
        ["jane-doe"],
        "2022-12-31",
        cycle=2022,
        support_oppose="oppose",
        amount=500.0,
        committee_id="C00000001",
        committee_name="PAC One",
        fec_candidate_id="P00000001",
    ),
    make(
        "disclosure",
        "disclosure-jane-doe-2024-10011111",
        ["jane-doe"],
        "2024-05-15",
        filer_name="Jane Doe",
        year=2024,
        form="P",
        filing_date="2024-05-15",
        document_url="https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024/10011111.pdf",
    ),
    make(
        "disclosure",
        "disclosure-jane-doe-2023-10000001",
        ["jane-doe"],
        "2023-05-15",
        filer_name="Jane Doe",
        year=2023,
        form="A",
        filing_date="2023-05-15",
        document_url="https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2023/10000001.pdf",
    ),
    make(
        "endorsement",
        "endorsement-jane-doe-b",
        ["jane-doe"],
        "2024-05-01",
        endorser="Sam Lee",
        endorser_type="person",
        date="2024-05-01",
    ),
    make(
        "endorsement",
        "endorsement-jane-doe-a",
        ["jane-doe"],
        "2024-01-01",
        endorser="Ann Park",
        endorser_type="organization",
        date="2024-01-01",
    ),
    make(
        "appearance",
        "appearance-jane-doe-debate",
        ["jane-doe"],
        "2024-09-10",
        event="Debate",
        venue="Hall",
        host="ABC",
        date="2024-09-10",
        transcript_url=None,
        video_url=None,
    ),
    make(
        "poll",
        "poll-jane-doe-late",
        ["jane-doe"],
        "2024-10-18",
        pollster="Pollco",
        value=48.0,
        field_start="2024-10-14",
        field_end="2024-10-18",
        sample=1000,
        population="likely voters",
    ),
    make(
        "poll",
        "poll-jane-doe-early",
        ["jane-doe"],
        "2024-09-05",
        pollster="Pollco",
        value=46.0,
        field_start="2024-09-01",
        field_end="2024-09-05",
        sample=800,
        population="registered voters",
    ),
    make(
        "article",
        "article-npr-jane-doe-1",
        ["jane-doe"],
        "2024-10-02",
        topics=["guns"],
        outlet_id="npr",
        headline="Doe on guns",
        author="Staff",
        archive_url=None,
        extraction_status="pending",
    ),
    make(
        "article",
        "article-npr-jane-doe-old",
        ["jane-doe"],
        "2023-01-04",
        outlet_id="npr",
        headline="Doe in 2023",
        author="Staff",
        archive_url=None,
        extraction_status="pending",
    ),
    make(
        "article",
        "article-nyt-john-roe-1",
        ["john-roe"],
        "2024-10-03",
        outlet_id="nyt",
        headline="Roe on guns",
        author="Staff",
        archive_url=None,
        extraction_status="pending",
    ),
    make(
        "position",
        "position-jane-doe-2024-08-01",
        ["jane-doe"],
        "2024-08-01",
        topics=["guns"],
        url="https://example.com/platform",
        capture_date="2024-08-01",
        archive_url=None,
        content_sha256=HASH,
        changed=False,
        key_quotes=[],
    ),
    make(
        "statement",
        "statement-jane-doe-guns",
        ["jane-doe"],
        "2024-08-10",
        topics=["guns"],
        quote="We will protect gun rights.",
        speaker="Jane Doe",
        venue="Rally",
        context=None,
        archive_url=None,
    ),
]


@pytest.fixture
def root(seeded_root):
    for rec in EXTRA:
        write_record(rec, seeded_root)
    server.configure(seeded_root)
    return seeded_root


def test_all_spec_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == SPEC_TOOLS


def test_get_bio_sorted_by_start_date(root):
    res = server.get_bio("jane-doe")
    assert [r["id"] for r in res["results"]] == ["bio-jane-doe-2005", "bio-jane-doe-2015"]
    assert res["count"] == 2 and res["truncated"] is False
    assert all(r["source_url"] for r in res["results"])


def test_get_outside_spending_filters_by_cycle(root):
    res = server.get_outside_spending("jane-doe", cycle=2024)
    assert [r["cycle"] for r in res["results"]] == [2024]
    assert res["count"] == 1
    everything = server.get_outside_spending("jane-doe")
    assert [r["cycle"] for r in everything["results"]] == [2022, 2024]


def test_get_disclosures_oldest_first(root):
    res = server.get_disclosures("jane-doe")
    assert [r["year"] for r in res["results"]] == [2023, 2024]


def test_get_endorsements_oldest_first(root):
    res = server.get_endorsements("jane-doe")
    assert [r["endorser"] for r in res["results"]] == ["Ann Park", "Sam Lee"]


def test_get_appearances(root):
    res = server.get_appearances("jane-doe")
    assert [r["event"] for r in res["results"]] == ["Debate"]


def test_get_polls_sorted_by_field_end(root):
    res = server.get_polls("jane-doe")
    assert [r["field_end"] for r in res["results"]] == ["2024-09-05", "2024-10-18"]
    assert all(r["pollster"] for r in res["results"])


def test_media_attention_counts_per_candidate_and_outlet(root):
    res = server.media_attention(period="2024")
    rows = {(r["candidate_id"], r["outlet_id"]): r["article_count"] for r in res["results"]}
    assert rows == {("jane-doe", "npr"): 1, ("john-roe", "nyt"): 1}
    assert res["count"] == 2
    assert set(res["results"][0]) >= {"candidate_id", "outlet_id", "article_count", "article_ids"}


def test_media_attention_filters_by_candidate_and_outlet(root):
    res = server.media_attention(candidate="jane-doe")
    assert {r["outlet_id"] for r in res["results"]} == {"npr"}
    assert [r["article_count"] for r in res["results"]] == [2]
    res = server.media_attention(outlet="nyt")
    assert [r["candidate_id"] for r in res["results"]] == ["john-roe"]


def test_media_attention_rejects_bad_period(root):
    assert "error" in server.media_attention(period="2024-13-99")


def test_compare_keeps_input_order_and_has_no_ordering_fields(root):
    res = server.compare(["john-roe", "jane-doe"], "guns")
    assert [g["candidate_id"] for g in res["results"]] == ["john-roe", "jane-doe"]
    assert set(res) == {"results", "count", "truncated", "note"}
    for group in res["results"]:
        assert not ({"rank", "score", "order", "ranking", "winner"} & set(group))
    jane = res["results"][1]["evidence"]
    assert all(r["source_url"] for r in jane)


def test_compare_unknown_id_lists_valid_ids(root):
    res = server.compare(["jane-doe", "nobody"], "guns")
    assert "error" in res
    assert "john-roe" in res["error"] and "jane-doe" in res["error"]


def test_position_timeline_uses_only_position_types(root):
    res = server.position_timeline("jane-doe", "guns")
    types = {r["type"] for r in res["results"]}
    assert types <= {"statement", "position", "vote", "bill", "executive_action"}
    assert {"statement", "position", "vote"} <= types
    dates = [r["published_at"] for r in res["results"]]
    assert dates == sorted(dates)


def test_search_evidence_covers_spec_evidence_types_only(root):
    types = {r["type"] for r in server.search_evidence("jane-doe", limit=500)["results"]}
    assert {"endorsement", "appearance", "poll", "article", "statement", "position", "vote"} <= types
    assert not ({"bio", "disclosure", "outside_spending", "finance", "candidate"} & types)


def test_every_tool_result_has_the_common_shape(root):
    results = [
        server.get_bio("jane-doe"),
        server.get_outside_spending("jane-doe"),
        server.get_disclosures("jane-doe"),
        server.get_endorsements("jane-doe"),
        server.get_appearances("jane-doe"),
        server.get_polls("jane-doe"),
        server.media_attention(),
        server.compare(["jane-doe"], "guns"),
    ]
    for res in results:
        assert set(res) == {"results", "count", "truncated", "note"}
        assert res["count"] == len(res["results"])

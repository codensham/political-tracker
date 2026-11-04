import httpx

from tracker.collectors import REGISTRY
from tracker.collectors.federal_register import FederalRegisterCollector
from tracker.validate import validate_record

API = "https://www.federalregister.gov/api/v1/documents.json"

EO_ROW = {
    "document_number": "2017-01799",
    "title": "Minimizing the Economic Burden of the Patient Protection and Affordable Care Act Pending Repeal",
    "publication_date": "2017-01-24",
    "signing_date": "2017-01-20",
    "html_url": "https://www.federalregister.gov/documents/2017/01/24/2017-01799/minimizing-the-economic-burden",
    "executive_order_number": "13765",
    "president": {"identifier": "donald-trump", "name": "Donald Trump"},
    "type": "Presidential Document",
}

TRUMP = {
    "id": "donald-trump",
    "type": "candidate",
    "candidate_ids": ["donald-trump"],
    "fec_candidate_ids": ["P80001571"],
}


def fr_client(pages_by_type: dict[str, list[dict]], calls: list[tuple[str, str]] | None = None):
    """pages_by_type maps a document type to its result pages; page N is served for ?page=N."""

    def handler(request: httpx.Request) -> httpx.Response:
        doc_type = request.url.params.get("conditions[presidential_document_type][]")
        page = int(request.url.params.get("page", "1"))
        if calls is not None:
            calls.append((doc_type, str(page)))
        pages = pages_by_type.get(doc_type, [])
        if not pages:
            return httpx.Response(200, json={"count": 0, "next_page_url": None, "results": []})
        index = page - 1
        body = pages[index]
        next_url = (
            f"{API}?conditions[presidential_document_type][]={doc_type}&page={page + 1}"
            if index + 1 < len(pages)
            else None
        )
        return httpx.Response(200, json={"count": 0, "next_page_url": next_url, "results": body})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_maps_executive_order():
    client = fr_client({"executive_order": [[EO_ROW]]})
    records = list(FederalRegisterCollector(client, sleep=lambda s: None).collect([TRUMP]))
    assert len(records) == 1
    rec = records[0]

    assert rec["id"] == "exec-2017-01799"
    assert rec["type"] == "executive_action"
    assert rec["candidate_ids"] == ["donald-trump"]
    assert rec["source_url"] == EO_ROW["html_url"]
    assert rec["published_at"] == "2017-01-24"
    assert rec["topics"] == []
    assert rec["document_type"] == "executive_order"
    assert rec["document_number"] == "2017-01799"
    assert rec["title"] == EO_ROW["title"]
    assert rec["signing_date"] == "2017-01-20"
    assert rec["executive_order_number"] == "13765"


def test_follows_next_page_until_done():
    second = {**EO_ROW, "document_number": "2017-02029", "html_url": "https://www.federalregister.gov/x"}
    calls: list[tuple[str, str]] = []
    client = fr_client({"executive_order": [[EO_ROW], [second]]}, calls)
    records = list(FederalRegisterCollector(client, sleep=lambda s: None).collect([TRUMP]))
    assert [r["document_number"] for r in records] == ["2017-01799", "2017-02029"]
    assert ("executive_order", "1") in calls
    assert ("executive_order", "2") in calls


def test_unmapped_candidate_makes_no_calls():
    calls: list[tuple[str, str]] = []
    other = {**TRUMP, "id": "jane-doe", "candidate_ids": ["jane-doe"]}
    client = fr_client({"executive_order": [[EO_ROW]]}, calls)
    records = list(FederalRegisterCollector(client, sleep=lambda s: None).collect([other]))
    assert records == []
    assert calls == []


def test_null_signing_date_is_allowed():
    row = {**EO_ROW, "signing_date": None, "executive_order_number": None}
    client = fr_client({"executive_order": [[row]]})
    rec = next(FederalRegisterCollector(client, sleep=lambda s: None).collect([TRUMP]))
    assert rec["signing_date"] is None
    assert rec["executive_order_number"] is None


def test_mapped_record_validates():
    client = fr_client({"executive_order": [[EO_ROW]]})
    rec = next(FederalRegisterCollector(client, sleep=lambda s: None).collect([TRUMP]))
    stamped = {**rec, "collector": "federal_register@1.0", "collected_at": "2026-11-04T09:00:00Z"}
    assert validate_record(stamped) == []


def test_registered_for_cli():
    assert REGISTRY["federal_register"] is FederalRegisterCollector


def test_slugs_cover_exactly_the_presidents_who_held_office():
    from tracker.collectors.federal_register import PRESIDENT_SLUGS

    assert set(PRESIDENT_SLUGS) == {"george-w-bush", "barack-obama", "donald-trump", "joe-biden"}


def test_non_holders_yield_no_executive_actions():
    from tracker.collectors.federal_register import PRESIDENT_SLUGS

    for cid in ("al-gore", "john-kerry", "john-mccain", "mitt-romney", "hillary-clinton", "kamala-harris"):
        assert cid not in PRESIDENT_SLUGS

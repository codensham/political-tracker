import json

import httpx

from tracker.collectors import REGISTRY
from tracker.collectors.congress_bills import CongressBillsCollector, bill_url
from tracker.crosswalk import load_crosswalk
from tracker.validate import TAXONOMY_PATH, validate_record


def bill(**overrides):
    row = {
        "congress": 100,
        "introducedDate": "1987-05-20",
        "number": "1250",
        "policyArea": {"name": "Crime and Law Enforcement"},
        "title": "Criminal and Juvenile Justice Partnership Act of 1987",
        "type": "S",
        "url": "https://api.congress.gov/v3/bill/100/s/1250?format=json",
    }
    row.update(overrides)
    return row


def member_client(sponsored=None, cosponsored=None, page_size=250):
    """Serve member bill lists, honouring the offset parameter and a next link."""
    sponsored = sponsored or []
    cosponsored = cosponsored or []

    def handler(request: httpx.Request) -> httpx.Response:
        is_cosponsored = "cosponsored-legislation" in request.url.path
        rows = cosponsored if is_cosponsored else sponsored
        key = "cosponsoredLegislation" if is_cosponsored else "sponsoredLegislation"
        offset = int(request.url.params.get("offset", 0))
        page = rows[offset : offset + page_size]
        body = {"pagination": {"count": len(rows)}, key: page}
        if offset + page_size < len(rows):
            body["pagination"]["next"] = "more"
        return httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def member(**overrides):
    rec = {
        "id": "joe-biden",
        "candidate_ids": ["joe-biden"],
        "bioguide_id": "B000444",
        "fec_candidate_ids": [],
        "candidacies": [],
    }
    rec.update(overrides)
    return rec


def test_crosswalk_targets_exist_and_names_are_unique():
    cw = load_crosswalk()
    topic_ids = {t["id"] for t in json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))["topics"]}
    for area, topics in cw.items():
        assert set(topics) <= topic_ids, area
    raw = json.loads((TAXONOMY_PATH.parent / "policy_area_crosswalk.json").read_text(encoding="utf-8"))
    names = [m["policy_area"] for m in raw["mappings"]]
    assert len(names) == len(set(names))


def test_sponsored_bill_maps_with_crosswalk_topics():
    c = member_client(sponsored=[bill()])
    records = list(CongressBillsCollector(c, sleep=lambda s: None).collect([member()]))
    assert len(records) == 1
    rec = records[0]
    assert rec["id"] == "bill-100-s-1250-joe-biden"
    assert rec["type"] == "bill"
    assert rec["bill_number"] == "S1250"
    assert rec["role"] == "sponsor"
    assert rec["policy_area"] == "Crime and Law Enforcement"
    assert rec["topics"] == ["criminal-justice"]
    assert rec["tagged_by"] == "crosswalk@1"
    assert rec["published_at"] == "1987-05-20"
    assert rec["source_url"] == "https://www.congress.gov/bill/100th-congress/senate-bill/1250"
    assert (
        validate_record({**rec, "collected_at": "2026-11-04T00:00:00Z", "collector": "congress_bills@1.0"})
        == []
    )


def test_cosponsored_bills_have_cosponsor_role():
    c = member_client(cosponsored=[bill(number="7")])
    (rec,) = CongressBillsCollector(c, sleep=lambda s: None).collect([member()])
    assert rec["role"] == "cosponsor"


def test_amendments_without_type_are_skipped():
    amendment = {"congress": 102, "amendmentNumber": "694", "introducedDate": "1991-07-10", "type": None}
    c = member_client(sponsored=[amendment, bill()])
    assert len(list(CongressBillsCollector(c, sleep=lambda s: None).collect([member()]))) == 1


def test_unknown_policy_area_gets_no_topics_and_no_tag():
    c = member_client(sponsored=[bill(policyArea={"name": "Private Legislation"})])
    (rec,) = CongressBillsCollector(c, sleep=lambda s: None).collect([member()])
    assert rec["topics"] == []
    assert "tagged_by" not in rec


def test_bill_without_policy_area_is_allowed():
    c = member_client(sponsored=[bill(policyArea=None)])
    (rec,) = CongressBillsCollector(c, sleep=lambda s: None).collect([member()])
    assert rec["policy_area"] is None
    assert rec["topics"] == []


def test_candidate_without_bioguide_skipped():
    c = member_client(sponsored=[bill()])
    assert list(CongressBillsCollector(c, sleep=lambda s: None).collect([member(bioguide_id=None)])) == []


def test_pagination_follows_offset_until_no_next():
    rows = [bill(number=str(n)) for n in range(1, 254)]
    c = member_client(sponsored=rows)
    records = list(CongressBillsCollector(c, sleep=lambda s: None).collect([member()]))
    assert len(records) == 253


def test_bill_url_ordinals_and_resolutions():
    assert bill_url(101, "HR", "7") == "https://www.congress.gov/bill/101st-congress/house-bill/7"
    assert bill_url(111, "SRES", "12") == "https://www.congress.gov/bill/111th-congress/senate-resolution/12"
    assert bill_url(112, "S", "1") == "https://www.congress.gov/bill/112th-congress/senate-bill/1"


def test_unknown_bill_type_skipped():
    c = member_client(sponsored=[bill(type="XYZ")])
    assert list(CongressBillsCollector(c, sleep=lambda s: None).collect([member()])) == []


def test_429_retried():
    seen = {"n": 0}

    def handler(request):
        seen["n"] += 1
        if seen["n"] == 1:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"pagination": {"count": 1}, "sponsoredLegislation": [bill()]})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    records = list(CongressBillsCollector(c, sleep=lambda s: None).collect([member()]))
    assert len(records) == 1
    assert seen["n"] >= 2


def test_registered():
    assert REGISTRY["congress_bills"] is CongressBillsCollector

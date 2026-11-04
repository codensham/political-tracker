import io
import zipfile

import httpx

from tracker.collectors.base import run_collector
from tracker.collectors.house_clerk import HouseClerkCollector, document_url, index_url
from tracker.records import load_records
from tracker.validate import validate_record

INDEX_XML = """<?xml version="1.0" encoding="utf-8"?>
<FinancialDisclosure>
  <Member>
    <Prefix></Prefix><First>Jane</First><Last>Doe</Last><Suffix></Suffix>
    <FilingType>P</FilingType><StateDst>NY12</StateDst><Year>2024</Year>
    <FilingDate>5/15/2024</FilingDate><DocID>10012345</DocID>
  </Member>
  <Member>
    <Prefix></Prefix><First>John</First><Last>Stranger</Last><Suffix></Suffix>
    <FilingType>A</FilingType><StateDst>TX07</StateDst><Year>2024</Year>
    <FilingDate>2/1/2024</FilingDate><DocID>10099999</DocID>
  </Member>
  <Member>
    <Prefix></Prefix><First>Jane</First><Last>Doe</Last><Suffix>Jr.</Suffix>
    <FilingType>A</FilingType><StateDst>NY12</StateDst><Year>2024</Year>
    <FilingDate>3/3/2024</FilingDate><DocID>10011111</DocID>
  </Member>
</FinancialDisclosure>"""


def zipped(xml: str, year: int = 2024) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{year}FD.xml", xml)
    return buf.getvalue()


def clerk_client(payload: bytes, calls: list[str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        return httpx.Response(200, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def candidate(cid: str, names: list[str]) -> dict:
    return {
        "id": cid,
        "type": "candidate",
        "candidate_ids": [cid],
        "source_url": "https://example.com/",
        "published_at": "2026-11-04",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "candidates@1.0",
        "topics": [],
        "name": "Jane Doe",
        "aliases": ["Jane Doe"],
        "candidacies": [],
        "fec_candidate_ids": [],
        "icpsr": None,
        "bioguide_id": None,
        "official_site": None,
        "inclusion_reason": "test",
        "disclosure_names": names,
    }


def test_registered_under_its_name():
    from tracker.collectors import BUILTIN_MODULES

    assert HouseClerkCollector.name == "house_clerk"
    assert "tracker.collectors.house_clerk" in BUILTIN_MODULES


def test_urls_follow_clerk_layout():
    assert index_url(2024) == "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024FD.zip"
    assert document_url(2024, "10012345") == (
        "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024/10012345.pdf"
    )


def test_index_rows_become_records_for_exact_name_matches(tmp_path):
    calls: list[str] = []
    client = clerk_client(zipped(INDEX_XML), calls)
    collector = HouseClerkCollector(client, years=[2024], sleep=lambda s: None)
    records = list(collector.collect([candidate("jane-doe", ["Jane Doe"])]))
    assert calls == [index_url(2024)]
    assert len(records) == 1
    rec = records[0]
    assert rec["type"] == "disclosure"
    assert rec["candidate_ids"] == ["jane-doe"]
    assert rec["filer_name"] == "Jane Doe"
    assert rec["year"] == 2024
    assert rec["form"] == "P"
    assert rec["filing_date"] == "2024-05-15"
    assert rec["document_url"].endswith("/10012345.pdf")


def test_name_not_in_config_is_skipped(tmp_path):
    client = clerk_client(zipped(INDEX_XML))
    collector = HouseClerkCollector(client, years=[2024], sleep=lambda s: None)
    records = list(
        collector.collect([candidate("jane-doe", ["Jane Doe"]), candidate("ghost", ["Nobody Here"])])
    )
    assert {r["candidate_ids"][0] for r in records} == {"jane-doe"}
    assert all(r["filer_name"] != "John Stranger" for r in records)


def test_matching_is_exact_not_fuzzy():
    client = clerk_client(zipped(INDEX_XML))
    collector = HouseClerkCollector(client, years=[2024], sleep=lambda s: None)
    # "Jane Doe Jr." is a different filer name from "Jane Doe"; only the exact string matches.
    records = list(collector.collect([candidate("jane-doe", ["Jane Doe Jr."])]))
    assert len(records) == 1
    assert records[0]["id"].endswith("-10011111")


def test_collected_records_validate(tmp_path):
    client = clerk_client(zipped(INDEX_XML))
    collector = HouseClerkCollector(client, years=[2024], sleep=lambda s: None)
    for rec in collector.collect([candidate("jane-doe", ["Jane Doe"])]):
        assert (
            validate_record({**rec, "collected_at": "2026-11-04T00:00:00Z", "collector": "house_clerk@1.0"})
            == []
        )


def test_unchanged_index_writes_nothing(tmp_path):
    # Seed the candidate record so the run has someone to match.
    from tracker.records import write_record

    write_record(candidate("jane-doe", ["Jane Doe"]), tmp_path)
    client = clerk_client(zipped(INDEX_XML))
    first = run_collector(HouseClerkCollector(client, years=[2024], sleep=lambda s: None), tmp_path)
    second = run_collector(HouseClerkCollector(client, years=[2024], sleep=lambda s: None), tmp_path)
    assert first.written == 1
    assert second.written == 0
    assert second.unchanged == 1
    assert len(list(load_records(tmp_path, "disclosure"))) == 1

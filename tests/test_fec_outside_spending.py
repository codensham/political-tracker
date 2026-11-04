import httpx

from tracker.collectors import REGISTRY
from tracker.collectors.base import run_collector
from tracker.collectors.fec_outside_spending import FecOutsideSpendingCollector
from tracker.records import load_records
from tracker.validate import validate_record, validate_tree

PATH = "/v1/schedules/schedule_e/by_candidate/"


def row(indicator="O", total=1086994.25, committee="C00004036", name="SEIU COPE"):
    return {
        "candidate_id": "P80001571",
        "cycle": 2024,
        "support_oppose_indicator": indicator,
        "total": total,
        "committee_id": committee,
        "committee_name": name,
    }


def client(pages):
    """pages: list of (results, total_pages); served in order of the requested page number."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        results, total_pages = pages[int(request.url.params["page"]) - 1]
        return httpx.Response(200, json={"results": results, "pagination": {"pages": total_pages}})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def candidate(**overrides):
    rec = {
        "id": "donald-trump",
        "candidacies": [{"year": 2024}, {"year": 2016}],
        "fec_candidate_ids": ["P80001571"],
    }
    rec.update(overrides)
    return rec


def test_maps_support_and_oppose():
    c, _ = client([([row("O"), row("S", total=5.0, committee="C00000001", name="X")], 1)])
    records = list(FecOutsideSpendingCollector(c, sleep=lambda s: None).collect([candidate()]))
    by_dir = {r["support_oppose"]: r for r in records if r["cycle"] == 2024}
    assert by_dir["oppose"]["amount"] == 1086994.25
    assert by_dir["oppose"]["committee_id"] == "C00004036"
    assert by_dir["support"]["amount"] == 5.0


def test_record_fields_and_id():
    c, _ = client([([row("O")], 1)])
    records = list(FecOutsideSpendingCollector(c, sleep=lambda s: None).collect([candidate()]))
    rec = next(r for r in records if r["cycle"] == 2024)
    assert rec["id"] == "outside-donald-trump-p80001571-2024-c00004036-oppose"
    assert rec["type"] == "outside_spending"
    assert rec["published_at"] == "2024-12-31"
    assert rec["source_url"] == "https://www.fec.gov/data/candidate/P80001571/?cycle=2024"
    assert (
        validate_record(
            {**rec, "collected_at": "2026-11-04T00:00:00Z", "collector": "fec_outside_spending@1.0"}
        )
        == []
    )


def test_pagination_follows_all_pages():
    c, calls = client([([row("O", committee="C00000001")], 2), ([row("S", committee="C00000002")], 2)])
    records = list(
        FecOutsideSpendingCollector(c, sleep=lambda s: None).collect(
            [candidate(candidacies=[{"year": 2024}])]
        )
    )
    assert [r["committee_id"] for r in records] == ["C00000001", "C00000002"]
    assert [p["page"] for p in calls] == ["1", "2"]


def test_one_request_per_cycle_and_fec_id():
    c, calls = client([([], 1)])
    list(FecOutsideSpendingCollector(c, sleep=lambda s: None).collect([candidate()]))
    assert sorted(p["cycle"] for p in calls) == ["2016", "2024"]
    assert {p["candidate_id"] for p in calls} == {"P80001571"}


def test_candidate_without_fec_ids_skipped():
    c, calls = client([([], 1)])
    assert (
        list(FecOutsideSpendingCollector(c, sleep=lambda s: None).collect([candidate(fec_candidate_ids=[])]))
        == []
    )
    assert calls == []


def test_rows_without_direction_skipped():
    c, _ = client([([row("X"), row("O", total=None)], 1)])
    assert list(FecOutsideSpendingCollector(c, sleep=lambda s: None).collect([candidate()])) == []


def test_429_retried():
    seen = {"n": 0}

    def handler(request):
        seen["n"] += 1
        if seen["n"] == 1:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"results": [row("O")], "pagination": {"pages": 1}})

    collector = FecOutsideSpendingCollector(
        httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda s: None
    )
    records = list(collector.collect([candidate(candidacies=[{"year": 2024}])]))
    assert len(records) == 1
    assert seen["n"] == 2


def test_registered_and_runs_into_finance_folder(tmp_path):
    assert REGISTRY["fec_outside_spending"] is FecOutsideSpendingCollector
    c, _ = client([([row("O")], 1)])
    from tracker.records import write_record

    write_record(
        {
            "id": "donald-trump",
            "type": "candidate",
            "candidate_ids": ["donald-trump"],
            "source_url": "https://www.fec.gov/",
            "published_at": "2026-11-04",
            "collected_at": "2026-11-04T00:00:00Z",
            "collector": "candidates@1.0",
            "topics": [],
            "name": "Donald J. Trump",
            "aliases": ["Donald Trump"],
            "candidacies": [
                {
                    "office": "president",
                    "year": 2024,
                    "party": "REP",
                    "result": "won",
                    "fec_candidate_id": "P80001571",
                    "source_url": "https://www.fec.gov/",
                }
            ],
            "fec_candidate_ids": ["P80001571"],
            "icpsr": None,
            "bioguide_id": None,
            "official_site": None,
            "inclusion_reason": "test",
        },
        tmp_path,
    )
    run_collector(FecOutsideSpendingCollector(c, sleep=lambda s: None), tmp_path)
    assert validate_tree(tmp_path) == {}
    assert [r["type"] for r in load_records(tmp_path, "outside_spending")] == ["outside_spending"]
    assert all(r["type"] == "candidate" for r in load_records(tmp_path, "candidate"))
    # finance-type loads must not pick up outside-spending records
    assert list(load_records(tmp_path, "finance")) == []

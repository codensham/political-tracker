import json
from pathlib import Path

import httpx

from tracker.collectors import REGISTRY
from tracker.collectors.__main__ import main as collectors_main
from tracker.collectors.base import run_collector
from tracker.collectors.fec import FecFinanceCollector
from tracker.records import write_record
from tracker.validate import validate_record, validate_tree

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "fec_totals.json").read_text(encoding="utf-8"))
FEC_ID = FIXTURE["candidate_id"]
ROW = FIXTURE["results"][0]
TOTALS_PATH = f"/v1/candidate/{FEC_ID}/totals/"

CANDIDATE = {
    "id": "jane-doe",
    "type": "candidate",
    "candidate_ids": ["jane-doe"],
    "fec_candidate_ids": [FEC_ID],
}


def fixture_client(calls: list[str] | None = None, statuses: list[int] | None = None):
    pending = list(statuses or [])

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        if pending:
            status = pending.pop(0)
            if status != 200:
                return httpx.Response(status, json={})
        if request.url.path == TOTALS_PATH:
            return httpx.Response(200, json=FIXTURE)
        return httpx.Response(404, json={})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_maps_fixture():
    records = list(FecFinanceCollector(fixture_client(), sleep=lambda s: None).collect([CANDIDATE]))
    assert len(records) == 1
    rec = records[0]

    assert rec["id"] == f"finance-jane-doe-{FEC_ID.lower()}-{ROW['cycle']}"
    assert rec["type"] == "finance"
    assert rec["candidate_ids"] == ["jane-doe"]
    assert rec["source_url"] == f"https://www.fec.gov/data/candidate/{FEC_ID}/?cycle={ROW['cycle']}"
    assert rec["topics"] == []
    assert rec["cycle"] == ROW["cycle"]
    assert rec["receipts"] == ROW["receipts"]
    assert rec["disbursements"] == ROW["disbursements"]
    assert rec["cash_on_hand_end"] == ROW["last_cash_on_hand_end_period"]
    assert rec["debts_owed"] == ROW["last_debts_owed_by_committee"]
    assert rec["coverage_start"] == ROW["coverage_start_date"][:10]
    assert rec["coverage_end"] == ROW["coverage_end_date"][:10]
    assert rec["published_at"] == rec["coverage_end"]
    assert rec["fec_candidate_id"] == FEC_ID


def test_records_validate(tmp_path: Path):
    collector = FecFinanceCollector(fixture_client(), sleep=lambda s: None)
    write_record(
        {
            **CANDIDATE,
            "source_url": "https://www.fec.gov/",
            "published_at": "2026-11-03",
            "collected_at": "2026-11-03T09:00:00Z",
            "collector": "candidates@1.0",
            "topics": [],
            "name": "Jane Doe",
            "party": "DEM",
            "status": "potential",
            "icpsr": None,
            "bioguide_id": None,
            "official_site": None,
            "inclusion_reason": "test",
        },
        tmp_path,
    )
    result = run_collector(collector, tmp_path)
    assert result.written == 1
    assert validate_tree(tmp_path) == {}
    assert (
        validate_record(
            {
                **next(collector.collect([CANDIDATE])),
                "collector": "fec_finance@1.0",
                "collected_at": "2026-11-03T09:00:00Z",
            }
        )
        == []
    )


def test_candidate_without_fec_ids_skipped():
    calls: list[str] = []
    no_ids = {**CANDIDATE, "fec_candidate_ids": []}
    records = list(FecFinanceCollector(fixture_client(calls), sleep=lambda s: None).collect([no_ids]))
    assert records == []
    assert calls == []


def test_429_retried():
    calls: list[str] = []
    client = fixture_client(calls, statuses=[429])
    records = list(FecFinanceCollector(client, sleep=lambda s: None).collect([CANDIDATE]))
    assert len(records) == 1
    assert calls == [TOTALS_PATH, TOTALS_PATH]


def test_cli_nonzero_on_failure(tmp_path: Path, monkeypatch):
    import tracker.collectors.fec  # noqa: F401  registers fec_finance once

    other_id = "P99999999"
    candidates = [
        CANDIDATE,
        {
            "id": "john-roe",
            "type": "candidate",
            "candidate_ids": ["john-roe"],
            "fec_candidate_ids": [other_id],
        },
    ]
    data = tmp_path / "data"
    from tracker.collectors import base as _base  # noqa: F401
    from tracker.records import write_record

    for cand in candidates:
        write_record(
            {
                **cand,
                "source_url": "https://www.fec.gov/",
                "published_at": "2026-11-03",
                "collected_at": "2026-11-03T09:00:00Z",
                "collector": "candidates@1.0",
                "topics": [],
                "name": cand["id"],
                "party": "DEM",
                "status": "potential",
                "icpsr": None,
                "bioguide_id": None,
                "official_site": None,
                "inclusion_reason": "test",
            },
            data,
        )

    def factory():
        # first candidate succeeds; second gets a persistent 500
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == TOTALS_PATH:
                return httpx.Response(200, json=FIXTURE)
            return httpx.Response(500, json={})

        return FecFinanceCollector(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda s: None)

    monkeypatch.setitem(REGISTRY, "fec_finance", factory)
    code = collectors_main(["fec_finance", "--data", str(data)])
    assert code != 0
    assert validate_tree(data) == {}
    assert any((data / "finance").rglob("*.json"))


def test_rows_with_null_fields_skipped_not_fatal():
    bad_debts = {**ROW, "last_debts_owed_by_committee": None}
    bad_start = {**ROW, "coverage_start_date": None, "cycle": 2029}
    good = {**ROW, "cycle": 2030}
    payload = {**FIXTURE, "results": [bad_debts, bad_start, good]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    records = list(FecFinanceCollector(client, sleep=lambda s: None).collect([CANDIDATE]))
    assert [r["cycle"] for r in records] == [2030]

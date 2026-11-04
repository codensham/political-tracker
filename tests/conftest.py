import pytest

from tracker.records import write_record

CANDIDATE_BASE = {
    "source_url": "https://www.fec.gov/data/candidate/P00000001/",
    "published_at": "2026-11-03",
    "collected_at": "2026-11-03T09:00:00Z",
    "collector": "candidates@1.0",
    "topics": [],
    "fec_candidate_ids": [],
    "icpsr": None,
    "bioguide_id": None,
    "official_site": None,
    "inclusion_reason": "test",
}


def candidate(cid: str, name: str, result: str, year: int = 2028) -> dict:
    return {
        **CANDIDATE_BASE,
        "id": cid,
        "type": "candidate",
        "candidate_ids": [cid],
        "name": name,
        "aliases": [name],
        "candidacies": [
            {
                "office": "president",
                "year": year,
                "party": "DEM",
                "result": result,
                "fec_candidate_id": None,
                "source_url": "https://www.fec.gov/data/candidate/P00000001/",
            }
        ],
    }


def vote(cid: str, rid: str, date: str, topics: list[str]) -> dict:
    return {
        "id": rid,
        "type": "vote",
        "candidate_ids": [cid],
        "source_url": f"https://voteview.com/rollcall/{rid}",
        "published_at": date,
        "collected_at": "2026-11-03T09:00:00Z",
        "collector": "voteview@1.0",
        "topics": topics,
        "chamber": "senate",
        "congress": 117,
        "rollnumber": 1,
        "vote_date": date,
        "cast": "yea",
    }


@pytest.fixture
def seeded_root(tmp_path):
    root = tmp_path / "data"
    write_record(candidate("jane-doe", "Jane Doe", "potential"), root)
    write_record(candidate("john-roe", "John Roe", "declared"), root)
    write_record(vote("jane-doe", "vote-s117-1-jane-doe", "2021-01-05", ["economy"]), root)
    write_record(vote("jane-doe", "vote-s117-2-jane-doe", "2021-06-01", ["guns"]), root)
    write_record(vote("jane-doe", "vote-s117-3-jane-doe", "2023-03-01", []), root)
    write_record(vote("john-roe", "vote-s117-1-john-roe", "2021-06-01", ["guns"]), root)
    write_record(
        {
            "id": "finance-jane-doe-p00000001-2028",
            "type": "finance",
            "candidate_ids": ["jane-doe"],
            "source_url": "https://www.fec.gov/data/candidate/P00000001/?cycle=2028",
            "published_at": "2027-06-30",
            "collected_at": "2026-11-03T09:00:00Z",
            "collector": "fec_finance@1.0",
            "topics": [],
            "cycle": 2028,
            "receipts": 1.0,
            "disbursements": 1.0,
            "cash_on_hand_end": 1.0,
            "debts_owed": 0.0,
            "coverage_start": "2027-01-01",
            "coverage_end": "2027-06-30",
            "fec_candidate_id": "P00000001",
        },
        root,
    )
    return root

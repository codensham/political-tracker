from tracker.tagging import normalize_bill_number, tag_votes_from_bills


def test_normalize_bill_number_forms():
    assert normalize_bill_number("H.R.1") == "HR1"
    assert normalize_bill_number("HR 1") == "HR1"
    assert normalize_bill_number("S. 1250") == "S1250"
    assert normalize_bill_number("S.Res.12") == "SRES12"
    assert normalize_bill_number(None) is None


def vote(cid, rnum, bill_number, congress=117):
    return {
        "id": f"vote-{rnum}-{cid}",
        "type": "vote",
        "candidate_ids": [cid],
        "source_url": "https://voteview.com/rollcall/x",
        "published_at": "2021-06-01",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "voteview@1.0",
        "topics": [],
        "chamber": "house",
        "congress": congress,
        "rollnumber": rnum,
        "vote_date": "2021-06-01",
        "question": None,
        "bill_number": bill_number,
        "vote_result": None,
        "cast": "yea",
    }


def bill(number, topics, area="Health", congress=117):
    return {
        "id": f"bill-{congress}-hr-{number}-joe-biden",
        "type": "bill",
        "candidate_ids": ["joe-biden"],
        "source_url": "https://www.congress.gov/bill/117th-congress/house-bill/1",
        "published_at": "2021-01-01",
        "collected_at": "2026-11-04T00:00:00Z",
        "collector": "congress_bills@1.0",
        "topics": topics,
        "congress": congress,
        "bill_number": f"HR{number}",
        "title": "Test",
        "policy_area": area,
        "role": "sponsor",
        "introduced_date": "2021-01-01",
    }


def test_vote_takes_topics_and_policy_area_from_matching_bill():
    (out,) = tag_votes_from_bills([vote("joe-biden", 1, "H.R.1")], [bill(1, ["healthcare"])])
    assert out["topics"] == ["healthcare"]
    assert out["policy_area"] == "Health"
    assert out["tagged_by"] == "crosswalk@1"


def test_vote_without_matching_bill_unchanged():
    (out,) = tag_votes_from_bills([vote("joe-biden", 2, "H.R.99")], [bill(1, ["healthcare"])])
    assert out["topics"] == []
    assert "policy_area" not in out
    assert "tagged_by" not in out


def test_match_requires_same_congress():
    (out,) = tag_votes_from_bills(
        [vote("joe-biden", 3, "H.R.1", congress=116)], [bill(1, ["healthcare"], congress=117)]
    )
    assert out["topics"] == []


def test_vote_without_bill_number_unchanged():
    (out,) = tag_votes_from_bills([vote("joe-biden", 4, None)], [bill(1, ["healthcare"])])
    assert out["topics"] == []


def test_retag_votes_writes_only_changed_votes(tmp_path):
    from tracker.records import load_records, write_record
    from tracker.tagging import retag_votes

    write_record(bill(1, ["healthcare"]), tmp_path)
    write_record(vote("joe-biden", 1, "H.R.1"), tmp_path)
    write_record(vote("joe-biden", 2, "H.R.99"), tmp_path)
    assert retag_votes(tmp_path) == 1
    tagged = {v["rollnumber"]: v for v in load_records(tmp_path, "vote")}
    assert tagged[1]["topics"] == ["healthcare"]
    assert tagged[2]["topics"] == []
    assert retag_votes(tmp_path) == 0

import time

from tracker.mcp_server import cache
from tracker.mcp_server.index import DataIndex
from tracker.records import write_record
from tracker.validate import REPO_ROOT


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


def cache_path_for(root):
    return root.parent / ".cache" / "index.sqlite"


def test_cache_file_is_created_outside_the_data_folder(seeded_root):
    DataIndex.load(seeded_root)
    assert cache_path_for(seeded_root).exists()
    assert not (seeded_root / "index.sqlite").exists()


def test_second_load_reads_the_cache_not_the_json(seeded_root, monkeypatch):
    first = DataIndex.load(seeded_root)

    def no_json(*args, **kwargs):
        raise AssertionError("JSON read on a warm cache")

    monkeypatch.setattr(cache, "load_records", no_json)
    second = DataIndex.load(seeded_root)
    assert second._records == first._records
    assert second.candidates() == first.candidates()


def test_new_record_invalidates_the_cache(seeded_root):
    DataIndex.load(seeded_root)
    write_record(
        make(
            "poll",
            "poll-jane-doe-new",
            ["jane-doe"],
            "2024-10-01",
            pollster="Pollco",
            value=40.0,
            field_start="2024-09-28",
            field_end="2024-10-01",
            sample=None,
            population="adults",
        ),
        seeded_root,
    )
    reloaded = DataIndex.load(seeded_root)
    assert [r["id"] for r in reloaded.polls("jane-doe")] == ["poll-jane-doe-new"]


def test_real_data_startup_under_five_seconds():
    data = REPO_ROOT / "data"
    DataIndex.load(data)  # cold build of the cache, if needed; the cold time is logged in DECISIONS.md
    start = time.perf_counter()
    DataIndex.load(data)
    elapsed = time.perf_counter() - start
    assert elapsed < 5, f"warm startup took {elapsed:.2f}s"


def test_cache_directory_is_git_ignored():
    assert ".cache/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

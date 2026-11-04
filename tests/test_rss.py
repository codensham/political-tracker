import httpx
import pytest

from tracker.archive import archive_url_for
from tracker.collectors import REGISTRY
from tracker.collectors.rss import FeedFailures, RssCollector, parse_feed
from tracker.matching import matched_candidate_ids
from tracker.validate import validate_record

RSS = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<item>
  <title>Donald Trump signs order on trade</title>
  <link>https://news.example/trump-trade</link>
  <pubDate>Mon, 03 Nov 2026 14:00:00 GMT</pubDate>
  <dc:creator>Jane Reporter</dc:creator>
  <description>The president spoke about tariffs.</description>
</item>
<item>
  <title>Trump critics respond</title>
  <link>https://news.example/critics</link>
  <pubDate>Mon, 03 Nov 2026 15:00:00 GMT</pubDate>
  <description>Trump was mentioned only by surname in the body.</description>
</item>
<item>
  <title>Unrelated story</title>
  <link>https://news.example/other</link>
  <pubDate>Mon, 03 Nov 2026 16:00:00 GMT</pubDate>
  <description>Nothing about candidates here.</description>
</item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry>
  <title>Harris campaign event</title>
  <link rel="alternate" href="https://atom.example/harris"/>
  <published>2026-11-02T10:00:00Z</published>
  <author><name>Sam Writer</name></author>
  <summary>Kamala Harris spoke today.</summary>
</entry>
</feed>"""

CANDIDATES = [
    {"id": "donald-trump", "name": "Donald J. Trump", "aliases": ["Donald Trump"]},
    {"id": "kamala-harris", "name": "Kamala Harris", "aliases": ["Kamala D. Harris"]},
]
OUTLETS = [
    {"id": "wire", "feed_url": "https://feeds.example/rss"},
    {"id": "atom", "feed_url": "https://feeds.example/atom"},
]


def client(routes, archive_ok=True):
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "web.archive.org" and request.url.path.startswith("/save/"):
            if not archive_ok:
                return httpx.Response(500, text="no")
            return httpx.Response(
                302,
                headers={
                    "location": "https://web.archive.org/web/20261104000000/"
                    + str(request.url).split("/save/", 1)[1]
                },
            )
        if host == "web.archive.org":
            return httpx.Response(200, text="snapshot")
        if str(request.url) in routes:
            return httpx.Response(200, content=routes[str(request.url)])
        return httpx.Response(404, text="missing")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_rss_and_atom():
    items = parse_feed(RSS)
    assert items[0]["title"] == "Donald Trump signs order on trade"
    assert items[0]["author"] == "Jane Reporter"
    assert items[0]["link"] == "https://news.example/trump-trade"
    atom = parse_feed(ATOM)
    assert atom[0]["link"] == "https://atom.example/harris"
    assert atom[0]["author"] == "Sam Writer"


def test_matching_full_name_and_alias_only():
    assert matched_candidate_ids("Donald J. Trump wins", CANDIDATES) == ["donald-trump"]
    assert matched_candidate_ids("Donald Trump wins", CANDIDATES) == ["donald-trump"]


def test_bare_surname_never_matches():
    assert matched_candidate_ids("Trump critics respond", CANDIDATES) == []
    assert matched_candidate_ids("Harris campaign event", CANDIDATES) == []


def test_partial_word_does_not_match():
    assert matched_candidate_ids("Donald Trumpet festival", CANDIDATES) == []


def test_collects_matching_items_only_and_validates():
    c = client({"https://feeds.example/rss": RSS, "https://feeds.example/atom": ATOM})
    records = list(RssCollector(c, outlets=OUTLETS, archive=False, sleep=lambda s: None).collect(CANDIDATES))
    assert [r["headline"] for r in records] == [
        "Donald Trump signs order on trade",
        "Harris campaign event",
    ]
    trump = next(r for r in records if r["source_url"] == "https://news.example/trump-trade")
    assert trump["candidate_ids"] == ["donald-trump"]
    assert trump["published_at"] == "2026-11-03"
    assert trump["extraction_status"] == "pending"
    assert trump["archive_url"] is None
    for r in records:
        assert validate_record({**r, "collected_at": "2026-11-04T00:00:00Z", "collector": "rss@1.0"}) == []


def test_no_article_text_is_stored():
    c = client({"https://feeds.example/rss": RSS, "https://feeds.example/atom": ATOM})
    records = list(RssCollector(c, outlets=OUTLETS, archive=False, sleep=lambda s: None).collect(CANDIDATES))
    for r in records:
        assert "summary" not in r and "description" not in r
        assert "tariffs" not in str(r)


def test_one_outlet_failing_still_writes_the_rest():
    c = client({"https://feeds.example/atom": ATOM})  # wire feed 404s
    gen = RssCollector(c, outlets=OUTLETS, archive=False, sleep=lambda s: None).collect(CANDIDATES)
    got = []
    with pytest.raises(FeedFailures) as info:
        for r in gen:
            got.append(r)
    assert [r["outlet_id"] for r in got] == ["atom"]
    assert any("wire" in f for f in info.value.failures)


def test_archive_url_recorded_when_saved():
    c = client({"https://feeds.example/rss": RSS, "https://feeds.example/atom": ATOM})
    records = list(RssCollector(c, outlets=OUTLETS, archive=True, sleep=lambda s: None).collect(CANDIDATES))
    trump = next(r for r in records if r["source_url"] == "https://news.example/trump-trade")
    assert trump["archive_url"].startswith("https://web.archive.org/web/")


def test_archive_failure_leaves_null_and_record_valid():
    c = client({"https://feeds.example/rss": RSS, "https://feeds.example/atom": ATOM}, archive_ok=False)
    records = list(RssCollector(c, outlets=OUTLETS, archive=True, sleep=lambda s: None).collect(CANDIDATES))
    assert records and all(r["archive_url"] is None for r in records)


def test_archive_retries_429_then_succeeds():
    seen = {"n": 0}

    def handler(request):
        if request.url.host == "web.archive.org" and request.url.path.startswith("/save/"):
            seen["n"] += 1
            if seen["n"] == 1:
                return httpx.Response(429)
            return httpx.Response(302, headers={"location": "https://web.archive.org/web/2026/x"})
        return httpx.Response(200, text="ok")

    result = archive_url_for(
        httpx.Client(transport=httpx.MockTransport(handler)), "https://x.example/a", sleep=lambda s: None
    )
    assert result == "https://web.archive.org/web/2026/x"
    assert seen["n"] == 2


def test_registered():
    assert REGISTRY["rss"] is RssCollector

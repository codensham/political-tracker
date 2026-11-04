"""Outlet RSS and Atom collector. Stores headline and metadata for items that name a tracked candidate.

No article text is stored (spec §5 content rules). The summary is read only to find candidate names.
"""

from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
import yaml

from tracker.archive import archive_url_for
from tracker.collectors import REGISTRY
from tracker.http import get_bytes
from tracker.matching import matched_candidate_ids
from tracker.validate import REPO_ROOT

OUTLETS_PATH = REPO_ROOT / "config" / "outlets.yaml"
DEFAULT_MAX_ARCHIVES = 25


class FeedFailures(RuntimeError):
    """Raised after every outlet was tried, so good records are still written (D-023)."""

    def __init__(self, failures: list[str]):
        super().__init__("feed failures: " + "; ".join(failures))
        self.failures = failures


def load_outlets(path: Path = OUTLETS_PATH) -> list[dict]:
    return list(yaml.safe_load(Path(path).read_text(encoding="utf-8"))["outlets"])


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(el: ET.Element, name: str) -> str | None:
    for child in el:
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return None


def parse_feed(body: bytes) -> list[dict]:
    """Return items with title, link, published, author and summary, for RSS or Atom."""
    root = ET.fromstring(body)
    items = []
    for el in root.iter():
        name = _local(el.tag)
        if name not in ("item", "entry"):
            continue
        link = _child_text(el, "link")
        if link is None:
            for child in el:
                if _local(child.tag) == "link" and child.get("href"):
                    link = child.get("href")
                    break
        author = _child_text(el, "creator") or _child_text(el, "author")
        if author is None:
            for child in el:
                if _local(child.tag) == "author":
                    author = _child_text(child, "name")
                    break
        items.append(
            {
                "title": _child_text(el, "title") or "",
                "link": link,
                "published": _child_text(el, "pubDate")
                or _child_text(el, "published")
                or _child_text(el, "updated"),
                "author": author,
                "summary": _child_text(el, "description") or _child_text(el, "summary") or "",
            }
        )
    return items


def _published_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _article_id(outlet_id: str, url: str) -> str:
    return f"article-{outlet_id}-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]}"


class RssCollector:
    name = "rss"
    version = "1.0"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        outlets: list[dict] | None = None,
        archive: bool = True,
        max_archives: int = DEFAULT_MAX_ARCHIVES,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(
            timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
        self._outlets = outlets if outlets is not None else load_outlets()
        self._archive = archive
        self._max_archives = max_archives
        self._sleep = sleep

    def collect(self, candidates: list[dict]) -> Iterable[dict]:
        failures: list[str] = []
        archived = 0
        for outlet in self._outlets:
            try:
                body = get_bytes(self._client, outlet["feed_url"], sleep=self._sleep)
                items = parse_feed(body)
            except (httpx.HTTPError, ET.ParseError) as exc:
                failures.append(f"{outlet['id']}: {exc}")
                continue
            for item in items:
                ids = matched_candidate_ids(f"{item['title']} {item['summary']}", candidates)
                if not ids or not item["link"]:
                    continue
                published = _published_date(item["published"])
                if published is None:
                    continue
                archive_url = None
                if self._archive and archived < self._max_archives:
                    archive_url = archive_url_for(self._client, item["link"], sleep=self._sleep)
                    archived += 1
                yield {
                    "id": _article_id(outlet["id"], item["link"]),
                    "type": "article",
                    "candidate_ids": ids,
                    "source_url": item["link"],
                    "archive_url": archive_url,
                    "published_at": published,
                    "topics": [],
                    "outlet_id": outlet["id"],
                    "headline": item["title"] or item["link"],
                    "author": item["author"],
                    "extraction_status": "pending",
                }
        if failures:
            raise FeedFailures(failures)


USER_AGENT = "political-tracker (+https://github.com/codensham/political-tracker)"

REGISTRY["rss"] = RssCollector

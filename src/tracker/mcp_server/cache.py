"""SQLite cache of the record set, rebuilt whenever a record file is added, removed or changed (D-029).

The JSON files stay canonical. The cache lives outside data/ in .cache/ (git-ignored) and is only a
faster way to load the same records. Freshness is a fingerprint of every .json path, size and mtime,
which is far cheaper to compute than reading and parsing every file.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

from tracker.records import load_records

SCHEMA_VERSION = "1"


def default_cache_path(root: Path) -> Path:
    return Path(root).resolve().parent / ".cache" / "index.sqlite"


def fingerprint(root: Path) -> str:
    root = Path(root)
    entries: list[str] = []

    def walk(directory: str) -> None:
        with os.scandir(directory) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    walk(entry.path)
                elif entry.name.endswith(".json"):
                    st = entry.stat(follow_symlinks=False)
                    rel = os.path.relpath(entry.path, root).replace("\\", "/")
                    entries.append(f"{rel}|{st.st_mtime_ns}|{st.st_size}")

    walk(str(root))
    digest = hashlib.sha256(SCHEMA_VERSION.encode("utf-8"))
    for line in sorted(entries):
        digest.update(line.encode("utf-8") + b"\n")
    return digest.hexdigest()


def _read_cache(cache_path: Path, fp: str) -> list[dict] | None:
    if not cache_path.exists():
        return None
    try:
        con = sqlite3.connect(cache_path)
        try:
            row = con.execute("SELECT value FROM meta WHERE key = 'fingerprint'").fetchone()
            if row is None or row[0] != fp:
                return None
            return [json.loads(data) for (data,) in con.execute("SELECT data FROM records ORDER BY rowid")]
        finally:
            con.close()
    except sqlite3.Error:
        return None


def _write_cache(cache_path: Path, fp: str, records: list[dict]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_name(cache_path.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    try:
        con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("CREATE TABLE records (id TEXT NOT NULL, type TEXT NOT NULL, data TEXT NOT NULL)")
        con.executemany(
            "INSERT INTO records (id, type, data) VALUES (?, ?, ?)",
            ((r["id"], r["type"], json.dumps(r, sort_keys=True)) for r in records),
        )
        con.execute("INSERT INTO meta (key, value) VALUES ('fingerprint', ?)", (fp,))
        con.commit()
    finally:
        con.close()
    os.replace(tmp, cache_path)


def load_records_cached(root: Path, cache_path: Path | None = None) -> list[dict]:
    """Every record under root. Reads the cache when its fingerprint matches, else rebuilds it."""
    root = Path(root)
    cache_path = Path(cache_path) if cache_path is not None else default_cache_path(root)
    fp = fingerprint(root)
    cached = _read_cache(cache_path, fp)
    if cached is not None:
        return cached
    records = list(load_records(root))
    _write_cache(cache_path, fp, records)
    return records

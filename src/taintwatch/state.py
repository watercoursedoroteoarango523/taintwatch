"""SQLite state: advisories, scan_runs, hits, alert_log, feeds."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from . import paths
from .models import Advisory, AffectedRange, Hit


SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS advisories (
    id            TEXT PRIMARY KEY,
    ecosystem     TEXT NOT NULL,
    name          TEXT NOT NULL,
    affected_json TEXT NOT NULL,
    summary       TEXT,
    severity      TEXT,
    source        TEXT NOT NULL,
    references_json TEXT NOT NULL DEFAULT '[]',
    first_seen    INTEGER NOT NULL,
    last_seen     INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_advisories_eco_name ON advisories(ecosystem, name);

CREATE TABLE IF NOT EXISTS scan_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    INTEGER NOT NULL,
    finished_at   INTEGER,
    repos_scanned INTEGER,
    hits_count    INTEGER
);

CREATE TABLE IF NOT EXISTS hits (
    scan_run_id   INTEGER NOT NULL REFERENCES scan_runs(id),
    advisory_id   TEXT NOT NULL REFERENCES advisories(id),
    ecosystem     TEXT NOT NULL,
    name          TEXT NOT NULL,
    version       TEXT NOT NULL,
    repo_path     TEXT NOT NULL,
    lockfile_path TEXT,
    installed_path TEXT,
    source        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hits_run ON hits(scan_run_id);
CREATE INDEX IF NOT EXISTS idx_hits_dedupe ON hits(advisory_id, repo_path, version);

CREATE TABLE IF NOT EXISTS alert_log (
    advisory_id  TEXT NOT NULL,
    repo_path    TEXT NOT NULL,
    channel      TEXT NOT NULL,
    sent_at      INTEGER NOT NULL,
    PRIMARY KEY (advisory_id, repo_path, channel)
);

CREATE TABLE IF NOT EXISTS feeds (
    name          TEXT PRIMARY KEY,
    last_etag     TEXT,
    last_fetched  INTEGER,
    status        TEXT
);

CREATE TABLE IF NOT EXISTS lockfile_cache (
    repo_path     TEXT NOT NULL,
    lockfile_path TEXT NOT NULL,
    mtime_ns      INTEGER NOT NULL,
    pkgs_json     TEXT NOT NULL,
    PRIMARY KEY (repo_path, lockfile_path)
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or paths.state_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def open_db(db_path: Path | None = None):
    conn = _connect(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA)
            cur = conn.execute("PRAGMA user_version")
            v = cur.fetchone()[0]
            if v < SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        yield conn
    finally:
        conn.close()


def upsert_advisory(conn: sqlite3.Connection, adv: Advisory) -> None:
    now = int(time.time())
    affected = json.dumps(
        {
            "versions": adv.versions,
            "ranges": [r.__dict__ for r in adv.ranges],
        }
    )
    refs = json.dumps(adv.references)
    conn.execute(
        """
        INSERT INTO advisories (id, ecosystem, name, affected_json, summary, severity,
                                source, references_json, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            ecosystem=excluded.ecosystem,
            name=excluded.name,
            affected_json=excluded.affected_json,
            summary=excluded.summary,
            severity=excluded.severity,
            source=excluded.source,
            references_json=excluded.references_json,
            last_seen=excluded.last_seen
        """,
        (
            adv.id,
            adv.ecosystem,
            adv.name,
            affected,
            adv.summary,
            adv.severity,
            adv.source,
            refs,
            now,
            now,
        ),
    )


def _row_to_advisory(row: sqlite3.Row) -> Advisory:
    affected = json.loads(row["affected_json"])
    refs = json.loads(row["references_json"]) if row["references_json"] else []
    return Advisory(
        id=row["id"],
        ecosystem=row["ecosystem"],
        name=row["name"],
        summary=row["summary"] or "",
        severity=row["severity"] or "",
        source=row["source"],
        versions=list(affected.get("versions", [])),
        ranges=[AffectedRange(**r) for r in affected.get("ranges", [])],
        references=refs,
    )


def advisories_for(conn: sqlite3.Connection, ecosystem: str, name: str) -> list[Advisory]:
    rows = conn.execute(
        "SELECT * FROM advisories WHERE ecosystem = ? AND name = ?",
        (ecosystem, name),
    ).fetchall()
    return [_row_to_advisory(r) for r in rows]


def get_advisory(conn: sqlite3.Connection, advisory_id: str) -> Advisory | None:
    row = conn.execute("SELECT * FROM advisories WHERE id = ?", (advisory_id,)).fetchone()
    return _row_to_advisory(row) if row else None


def count_advisories(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM advisories").fetchone()
    return int(row["n"])


def start_scan_run(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "INSERT INTO scan_runs (started_at) VALUES (?)", (int(time.time()),)
    )
    return int(cur.lastrowid)


def finish_scan_run(
    conn: sqlite3.Connection, run_id: int, repos_scanned: int, hits_count: int
) -> None:
    conn.execute(
        "UPDATE scan_runs SET finished_at=?, repos_scanned=?, hits_count=? WHERE id=?",
        (int(time.time()), repos_scanned, hits_count, run_id),
    )


def insert_hits(conn: sqlite3.Connection, run_id: int, hits: Iterable[Hit]) -> None:
    rows = [
        (
            run_id,
            h.advisory_id,
            h.pkg.ecosystem,
            h.pkg.name,
            h.pkg.version,
            str(h.pkg.repo_path),
            str(h.pkg.lockfile_path) if h.pkg.lockfile_path else None,
            str(h.pkg.installed_path) if h.pkg.installed_path else None,
            h.pkg.source,
        )
        for h in hits
    ]
    conn.executemany(
        """
        INSERT INTO hits (scan_run_id, advisory_id, ecosystem, name, version,
                          repo_path, lockfile_path, installed_path, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def last_completed_run(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        "SELECT id FROM scan_runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return int(row["id"]) if row else None


def hits_for_run(conn: sqlite3.Connection, run_id: int) -> list[tuple[str, str, str]]:
    """Return (advisory_id, repo_path, version) tuples for diffing."""
    rows = conn.execute(
        "SELECT advisory_id, repo_path, version FROM hits WHERE scan_run_id = ?",
        (run_id,),
    ).fetchall()
    return [(r["advisory_id"], r["repo_path"], r["version"]) for r in rows]


def alert_already_sent(
    conn: sqlite3.Connection, advisory_id: str, repo_path: str, channel: str
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM alert_log WHERE advisory_id=? AND repo_path=? AND channel=?",
        (advisory_id, repo_path, channel),
    ).fetchone()
    return row is not None


def record_alert(
    conn: sqlite3.Connection, advisory_id: str, repo_path: str, channel: str
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO alert_log (advisory_id, repo_path, channel, sent_at) "
        "VALUES (?, ?, ?, ?)",
        (advisory_id, repo_path, channel, int(time.time())),
    )


def get_feed_etag(conn: sqlite3.Connection, name: str) -> str | None:
    row = conn.execute("SELECT last_etag FROM feeds WHERE name = ?", (name,)).fetchone()
    return row["last_etag"] if row else None


def set_feed_status(
    conn: sqlite3.Connection, name: str, etag: str | None, status: str
) -> None:
    conn.execute(
        """
        INSERT INTO feeds (name, last_etag, last_fetched, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            last_etag=excluded.last_etag,
            last_fetched=excluded.last_fetched,
            status=excluded.status
        """,
        (name, etag, int(time.time()), status),
    )


def get_feeds_status(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM feeds ORDER BY name").fetchall()


def get_lockfile_cache(
    conn: sqlite3.Connection, repo_path: str, lockfile_path: str
) -> tuple[int, str] | None:
    row = conn.execute(
        "SELECT mtime_ns, pkgs_json FROM lockfile_cache WHERE repo_path=? AND lockfile_path=?",
        (repo_path, lockfile_path),
    ).fetchone()
    if not row:
        return None
    return int(row["mtime_ns"]), row["pkgs_json"]


def set_lockfile_cache(
    conn: sqlite3.Connection,
    repo_path: str,
    lockfile_path: str,
    mtime_ns: int,
    pkgs_json: str,
) -> None:
    conn.execute(
        """
        INSERT INTO lockfile_cache (repo_path, lockfile_path, mtime_ns, pkgs_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(repo_path, lockfile_path) DO UPDATE SET
            mtime_ns=excluded.mtime_ns,
            pkgs_json=excluded.pkgs_json
        """,
        (repo_path, lockfile_path, mtime_ns, pkgs_json),
    )

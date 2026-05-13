from __future__ import annotations

import time
from pathlib import Path

from taintwatch import feeds as feeds_mod
from taintwatch.config import Config, FeedsConfig
from taintwatch.state import open_db, set_feed_status


def _seed_feed(conn, name: str, age_seconds: int) -> None:
    set_feed_status(conn, name, etag=None, status="ok")
    # set_feed_status writes the current time; reach in to backdate it
    conn.execute(
        "UPDATE feeds SET last_fetched = ? WHERE name = ?",
        (int(time.time()) - age_seconds, name),
    )


def test_is_stale_when_no_feeds_rows(tmp_path: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "s.db")
    cfg = Config(feeds=FeedsConfig(osv=True, openssf=True, aikido=True, max_age_hours=24))
    with open_db() as conn:
        assert feeds_mod.is_stale(conn, cfg) is True
        assert feeds_mod.oldest_fetch_age_seconds(conn, cfg) is None


def test_is_stale_when_one_feed_missing(tmp_path: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "s.db")
    cfg = Config(feeds=FeedsConfig(osv=True, openssf=True, aikido=True, max_age_hours=24))
    with open_db() as conn:
        _seed_feed(conn, "osv", age_seconds=60)
        _seed_feed(conn, "openssf", age_seconds=60)
        # aikido row missing -> stale
        assert feeds_mod.is_stale(conn, cfg) is True


def test_not_stale_when_all_fresh(tmp_path: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "s.db")
    cfg = Config(feeds=FeedsConfig(osv=True, openssf=True, aikido=True, max_age_hours=24))
    with open_db() as conn:
        _seed_feed(conn, "osv", age_seconds=60)
        _seed_feed(conn, "openssf", age_seconds=60)
        _seed_feed(conn, "aikido", age_seconds=60)
        assert feeds_mod.is_stale(conn, cfg) is False
        age = feeds_mod.oldest_fetch_age_seconds(conn, cfg)
        assert age is not None and 50 <= age <= 120


def test_stale_when_one_feed_old(tmp_path: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "s.db")
    cfg = Config(feeds=FeedsConfig(osv=True, openssf=True, aikido=True, max_age_hours=24))
    with open_db() as conn:
        _seed_feed(conn, "osv", age_seconds=60)
        _seed_feed(conn, "openssf", age_seconds=60)
        _seed_feed(conn, "aikido", age_seconds=2 * 86400)  # 2 days
        assert feeds_mod.is_stale(conn, cfg) is True


def test_disabled_feed_does_not_block_freshness(tmp_path: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "s.db")
    # User has aikido disabled
    cfg = Config(feeds=FeedsConfig(osv=True, openssf=True, aikido=False, max_age_hours=24))
    with open_db() as conn:
        _seed_feed(conn, "osv", age_seconds=60)
        _seed_feed(conn, "openssf", age_seconds=60)
        # no aikido row, but aikido disabled -> shouldn't make it stale
        assert feeds_mod.is_stale(conn, cfg) is False

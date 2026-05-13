from __future__ import annotations

import sqlite3
import time
from typing import Iterable

from ..config import Config
from ..state import get_feeds_status
from . import aikido, openssf, osv
from .base import Fetcher


def oldest_fetch_age_seconds(conn: sqlite3.Connection, cfg: Config) -> int | None:
    """Seconds since the OLDEST enabled feed was last fetched.

    Returns None if any enabled feed has never been fetched — callers should
    treat that as "definitely stale, refresh now."
    """
    enabled = {f.name for f in enabled_fetchers(cfg)}
    rows = get_feeds_status(conn)
    seen = set()
    oldest = None
    for r in rows:
        if r["name"] not in enabled:
            continue
        seen.add(r["name"])
        if not r["last_fetched"]:
            return None
        age = int(time.time()) - int(r["last_fetched"])
        if oldest is None or age > oldest:
            oldest = age
    if seen != enabled:
        return None        # an enabled feed has no row yet
    return oldest


def is_stale(conn: sqlite3.Connection, cfg: Config) -> bool:
    """True if any enabled feed is older than cfg.feeds.max_age_hours or missing."""
    age = oldest_fetch_age_seconds(conn, cfg)
    if age is None:
        return True
    return age >= cfg.feeds.max_age_hours * 3600


def enabled_fetchers(cfg: Config) -> list[Fetcher]:
    out: list[Fetcher] = []
    if cfg.feeds.osv:
        out.append(osv.OsvFetcher())
    if cfg.feeds.openssf:
        out.append(openssf.OpenSsfFetcher())
    if cfg.feeds.aikido:
        out.append(aikido.AikidoFetcher())
    return out


def update_all(conn: sqlite3.Connection, cfg: Config, *, force: bool = False) -> dict[str, str]:
    results: dict[str, str] = {}
    for fetcher in enabled_fetchers(cfg):
        try:
            count = fetcher.update(conn, force=force)
            results[fetcher.name] = f"ok ({count} new/updated)"
        except Exception as e:  # noqa: BLE001
            results[fetcher.name] = f"error: {e.__class__.__name__}: {e}"
    return results


__all__ = [
    "Fetcher",
    "enabled_fetchers",
    "is_stale",
    "oldest_fetch_age_seconds",
    "update_all",
]

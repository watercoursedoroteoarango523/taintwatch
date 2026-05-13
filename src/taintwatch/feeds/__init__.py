from __future__ import annotations

import sqlite3
from typing import Iterable

from ..config import Config
from . import aikido, openssf, osv
from .base import Fetcher


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


__all__ = ["Fetcher", "enabled_fetchers", "update_all"]

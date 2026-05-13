from __future__ import annotations

import sqlite3

from ..config import Config
from ..models import Hit
from ..state import alert_already_sent, record_alert
from . import discord, report, stdout, toast
from .base import AlertChannel


def channels(cfg: Config) -> list[AlertChannel]:
    out: list[AlertChannel] = [stdout.StdoutChannel(), report.ReportChannel(cfg)]
    if cfg.alerts.discord.webhook:
        out.append(discord.DiscordChannel(cfg.alerts.discord.webhook))
    if cfg.alerts.toast.enabled:
        out.append(toast.ToastChannel())
    return out


def dispatch_new_hits(
    conn: sqlite3.Connection,
    cfg: Config,
    hits: list[Hit],
    new_keys: set[tuple[str, str, str]],
) -> dict[str, int]:
    """Dispatch alerts only for hits whose (advisory_id, repo, channel) is not in alert_log."""
    new_hits = [h for h in hits if (h.advisory_id, str(h.pkg.repo_path), h.pkg.version) in new_keys]
    counts: dict[str, int] = {}
    for ch in channels(cfg):
        sent = 0
        targeted = [
            h for h in new_hits
            if not alert_already_sent(conn, h.advisory_id, str(h.pkg.repo_path), ch.name)
        ]
        if not targeted:
            counts[ch.name] = 0
            continue
        try:
            ch.send(targeted)
            for h in targeted:
                record_alert(conn, h.advisory_id, str(h.pkg.repo_path), ch.name)
                sent += 1
        except Exception as e:  # noqa: BLE001
            # One channel's failure doesn't block the others; the unrecorded
            # hits will retry on the next scan.
            counts[ch.name] = -1
            continue
        counts[ch.name] = sent
    return counts

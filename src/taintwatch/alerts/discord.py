from __future__ import annotations

import httpx

from ..models import Hit
from .base import AlertChannel
from .severity import Severity


MAX_FIELDS_PER_EMBED = 10
MAX_EMBED_PER_MSG = 4
TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# Embed colors and title prefix per severity. Discord clients render the
# embed's left-border in this color, which is the at-a-glance signal.
_STYLE = {
    Severity.CRITICAL: (0xC0392B, ":rotating_light: CRITICAL — compromised code installed"),
    Severity.HIGH: (0xE67E22, ":warning: compromised package in lockfile"),
    Severity.INFO: (0x3498DB, ":information_source: taintwatch"),
}


class DiscordChannel(AlertChannel):
    name = "discord"

    def __init__(self, webhook_url: str) -> None:
        self.webhook = webhook_url

    def send(self, hits: list[Hit], severity: Severity = Severity.HIGH) -> None:
        if not hits:
            return
        color, title = _STYLE[severity]
        # @here for CRITICAL so the channel actually gets pinged when something
        # is on disk. HIGH/INFO are silent posts.
        prefix = "@here " if severity is Severity.CRITICAL else ""
        embeds = self._build_embeds(hits, color, title)
        with httpx.Client(timeout=TIMEOUT) as client:
            for chunk in _chunk(embeds, MAX_EMBED_PER_MSG):
                resp = client.post(
                    self.webhook,
                    json={
                        "content": f"{prefix}**taintwatch:** {len(hits)} new hit(s)",
                        "embeds": chunk,
                        "allowed_mentions": {"parse": ["everyone"]} if prefix else {"parse": []},
                    },
                )
                resp.raise_for_status()

    def _build_embeds(self, hits: list[Hit], color: int, title: str) -> list[dict]:
        out: list[dict] = []
        for chunk in _chunk(hits, MAX_FIELDS_PER_EMBED):
            fields = []
            for h in chunk:
                location = h.pkg.lockfile_path or h.pkg.installed_path or h.pkg.repo_path
                where_tag = (
                    "**ON DISK**" if h.pkg.source == "installed" else "lockfile"
                )
                fields.append(
                    {
                        "name": f"{h.pkg.name}@{h.pkg.version} ({h.pkg.ecosystem})",
                        "value": (
                            f"**Advisory:** `{h.advisory_id}` ({h.advisory.source})\n"
                            f"**Repo:** `{h.pkg.repo_path.name}`\n"
                            f"**Where:** `{location}` ({where_tag})"
                        ),
                        "inline": False,
                    }
                )
            out.append(
                {
                    "title": title,
                    "color": color,
                    "fields": fields,
                }
            )
        return out


def _chunk(seq, n):
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf

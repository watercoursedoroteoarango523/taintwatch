from __future__ import annotations

import httpx

from ..models import Hit
from .base import AlertChannel


MAX_FIELDS_PER_EMBED = 10
MAX_EMBED_PER_MSG = 4
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class DiscordChannel(AlertChannel):
    name = "discord"

    def __init__(self, webhook_url: str) -> None:
        self.webhook = webhook_url

    def send(self, hits: list[Hit]) -> None:
        if not hits:
            return
        embeds = self._build_embeds(hits)
        with httpx.Client(timeout=TIMEOUT) as client:
            for chunk in _chunk(embeds, MAX_EMBED_PER_MSG):
                resp = client.post(
                    self.webhook,
                    json={
                        "content": f"**taintwatch:** {len(hits)} new compromised-package hit(s)",
                        "embeds": chunk,
                    },
                )
                resp.raise_for_status()

    def _build_embeds(self, hits: list[Hit]) -> list[dict]:
        out: list[dict] = []
        for chunk in _chunk(hits, MAX_FIELDS_PER_EMBED):
            fields = []
            for h in chunk:
                location = h.pkg.lockfile_path or h.pkg.installed_path or h.pkg.repo_path
                fields.append(
                    {
                        "name": f"{h.pkg.name}@{h.pkg.version} ({h.pkg.ecosystem})",
                        "value": (
                            f"**Advisory:** `{h.advisory_id}` ({h.advisory.source})\n"
                            f"**Repo:** `{h.pkg.repo_path.name}`\n"
                            f"**Where:** `{location}`\n"
                            f"**Source:** {h.pkg.source}"
                        ),
                        "inline": False,
                    }
                )
            out.append(
                {
                    "title": "Compromised package detected",
                    "color": 0xE74C3C,
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

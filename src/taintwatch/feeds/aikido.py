"""Aikido Intel public malware list. Real-time signal for npm + PyPI.

Endpoints are read from AikidoSec/safe-chain (open-source). Records are a flat
JSON array of objects shaped roughly like {"name": "...", "version": "...", "reason": "..."}.
Schema is not formally documented; we tolerate variation defensively.
"""
from __future__ import annotations

import logging
import sqlite3

import httpx

from ..models import Advisory
from ..state import set_feed_status, upsert_advisory
from .base import Fetcher

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "npm": "https://malware-list.aikido.dev/malware_predictions.json",
    "PyPI": "https://malware-list.aikido.dev/malware_pypi.json",
}
TIMEOUT = httpx.Timeout(60.0, connect=15.0)


class AikidoFetcher(Fetcher):
    name = "aikido"

    def update(self, conn: sqlite3.Connection, *, force: bool = False) -> int:  # noqa: ARG002
        upserted = 0
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            for ecosystem, url in ENDPOINTS.items():
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, ValueError) as e:
                    logger.warning("aikido: %s failed: %s", url, e)
                    continue
                if not isinstance(data, list):
                    # Some Aikido endpoints wrap entries in a top-level key
                    data = data.get("packages") if isinstance(data, dict) else None
                    if not isinstance(data, list):
                        continue
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("name") or entry.get("package")
                    version = entry.get("version") or entry.get("ver")
                    if not name or not version:
                        continue
                    aid = f"AIKIDO-{ecosystem}-{name}-{version}"
                    adv = Advisory(
                        id=aid,
                        ecosystem=ecosystem,
                        name=name,
                        summary=entry.get("reason") or entry.get("description") or "Aikido Intel flagged this version as malicious.",
                        severity="HIGH",
                        source="aikido",
                        versions=[str(version)],
                        ranges=[],
                        references=[
                            entry.get("url", "https://intel.aikido.dev/")
                            or "https://intel.aikido.dev/"
                        ],
                    )
                    upsert_advisory(conn, adv)
                    upserted += 1
        set_feed_status(conn, self.name, etag=None, status=f"ok ({upserted})")
        return upserted

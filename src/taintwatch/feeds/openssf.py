"""OpenSSF malicious-packages fetcher.

Pulls the `osv/malicious/` tree from github.com/ossf/malicious-packages via
the GitHub archive tarball (no git binary required). Same OSV schema as osv.dev,
so reuses the same normalizer.
"""
from __future__ import annotations

import io
import json
import logging
import sqlite3
import tarfile

import httpx

from ..state import set_feed_status, upsert_advisory
from .base import Fetcher
from .osv import _to_advisories

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://github.com/ossf/malicious-packages/archive/refs/heads/main.tar.gz"
TIMEOUT = httpx.Timeout(120.0, connect=15.0)


class OpenSsfFetcher(Fetcher):
    name = "openssf"

    def update(self, conn: sqlite3.Connection, *, force: bool = False) -> int:  # noqa: ARG002
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            try:
                resp = client.get(ARCHIVE_URL)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("openssf: archive fetch failed: %s", e)
                set_feed_status(conn, self.name, etag=None, status=f"error: {e}")
                return 0

        upserted = 0
        try:
            with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tf:
                for member in tf:
                    if not member.isfile():
                        continue
                    # Path looks like: malicious-packages-main/osv/malicious/npm/foo/MAL-2025-1.json
                    parts = member.name.split("/")
                    if "osv" not in parts or "malicious" not in parts:
                        continue
                    if not member.name.endswith(".json"):
                        continue
                    f = tf.extractfile(member)
                    if not f:
                        continue
                    try:
                        data = json.loads(f.read())
                    except json.JSONDecodeError:
                        continue
                    for adv in _to_advisories(data):
                        adv.source = "openssf"
                        upsert_advisory(conn, adv)
                        upserted += 1
        except tarfile.TarError as e:
            logger.warning("openssf: tar parse failed: %s", e)
            set_feed_status(conn, self.name, etag=None, status=f"error: {e}")
            return upserted

        set_feed_status(conn, self.name, etag=None, status=f"ok ({upserted})")
        return upserted

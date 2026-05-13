"""OSV.dev bulk fetcher.

Downloads `https://osv-vulnerabilities.storage.googleapis.com/<ECOSYSTEM>/all.zip`
per supported ecosystem, parses every record, and upserts into SQLite. We keep
only records whose id starts with "MAL-" (true malicious-package advisories);
GHSA/CVE records about plain vulnerabilities are out of v1 scope.
"""
from __future__ import annotations

import io
import json
import logging
import sqlite3
import zipfile

import httpx

from ..models import Advisory, AffectedRange
from ..state import set_feed_status, upsert_advisory
from .base import Fetcher

logger = logging.getLogger(__name__)


ECOSYSTEMS = ("npm", "PyPI", "crates.io", "Go", "RubyGems")
BUCKET = "https://osv-vulnerabilities.storage.googleapis.com"
TIMEOUT = httpx.Timeout(60.0, connect=15.0)


class OsvFetcher(Fetcher):
    name = "osv"

    def update(self, conn: sqlite3.Connection, *, force: bool = False) -> int:  # noqa: ARG002
        upserted = 0
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            for eco in ECOSYSTEMS:
                url = f"{BUCKET}/{eco}/all.zip"
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning("osv: failed to fetch %s: %s", url, e)
                    continue
                try:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                        for name in zf.namelist():
                            if not name.endswith(".json"):
                                continue
                            try:
                                data = json.loads(zf.read(name))
                            except json.JSONDecodeError:
                                continue
                            advisories = _to_advisories(data)
                            for adv in advisories:
                                if not adv.id.startswith("MAL-"):
                                    continue
                                upsert_advisory(conn, adv)
                                upserted += 1
                except zipfile.BadZipFile:
                    logger.warning("osv: bad zip for %s", eco)
                    continue
        set_feed_status(conn, self.name, etag=None, status=f"ok ({upserted})")
        return upserted


def _to_advisories(rec: dict) -> list[Advisory]:
    """One OSV record can list multiple `affected` packages; emit one Advisory per (id, eco, name)."""
    advisories: list[Advisory] = []
    rec_id = rec.get("id")
    if not rec_id:
        return advisories
    summary = rec.get("summary") or rec.get("details", "")[:200]
    severity = ""
    if isinstance(rec.get("severity"), list) and rec["severity"]:
        severity = rec["severity"][0].get("score", "") or ""
    references = [r.get("url", "") for r in rec.get("references", []) if isinstance(r, dict)]
    for affected in rec.get("affected", []):
        pkg = affected.get("package", {})
        eco = pkg.get("ecosystem")
        name = pkg.get("name")
        if not eco or not name:
            continue
        versions = list(affected.get("versions", []) or [])
        ranges: list[AffectedRange] = []
        for r in affected.get("ranges", []) or []:
            rtype = r.get("type", "ECOSYSTEM")
            introduced = fixed = last_affected = None
            for ev in r.get("events", []) or []:
                if "introduced" in ev:
                    introduced = ev["introduced"]
                if "fixed" in ev:
                    fixed = ev["fixed"]
                if "last_affected" in ev:
                    last_affected = ev["last_affected"]
            ranges.append(
                AffectedRange(
                    type=rtype,
                    introduced=introduced,
                    fixed=fixed,
                    last_affected=last_affected,
                )
            )
        advisories.append(
            Advisory(
                id=rec_id,
                ecosystem=eco,
                name=name,
                summary=summary,
                severity=severity,
                source="osv",
                versions=versions,
                ranges=ranges,
                references=references,
            )
        )
    return advisories

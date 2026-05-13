"""Classify a batch of hits into one of three severity tiers.

The tiers map to escalating toast sounds so the user can tell from across the
room whether they need to act NOW vs. soon vs. just glance later.

- CRITICAL: at least one hit is installed ON DISK (in node_modules / site-packages).
  The malicious code can execute the next time a build, dev server, or import
  runs. Loop an alarm.
- HIGH:    hits exist but all are lockfile-only. The malicious code will be
  installed on the next `npm ci` / `pip install -r`. Default ding.
- INFO:    no hits, or only positive signal (a previously-flagged repo cleared).
  Soft chime; off by default.

The threshold between CRITICAL and HIGH is `source == "installed"` because that
is the only signal that distinguishes "compromised right now" from "compromised
on next install."
"""
from __future__ import annotations

from enum import Enum

from ..models import Hit


class Severity(str, Enum):
    INFO = "info"
    HIGH = "high"
    CRITICAL = "critical"


def classify(hits: list[Hit]) -> Severity:
    if not hits:
        return Severity.INFO
    if any(h.pkg.source == "installed" for h in hits):
        return Severity.CRITICAL
    return Severity.HIGH

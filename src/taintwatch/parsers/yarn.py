"""yarn.lock parser. Supports classic (v1) and berry (v6+).

The format is custom YAML-ish. We do a forgiving line-based parse — sufficient
to extract `name@spec` headers and the corresponding `version: X` value.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..models import InstalledPkg


HEADER_RE = re.compile(r'^(?:(["\'])(.+?)\1|([^\s].*?)):\s*$')
NAME_RE = re.compile(r'^(@?[^@\s,"\']+)(?:@[^,"\']+)?')


def parse(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    pkgs: set[InstalledPkg] = set()
    text = lockfile.read_text(encoding="utf-8")
    blocks = _split_blocks(text)
    for header, body in blocks:
        names = _names_from_header(header)
        version = _version_from_body(body)
        if not version:
            continue
        for name in names:
            pkgs.add(
                InstalledPkg(
                    ecosystem="npm",
                    name=name,
                    version=version,
                    source="lockfile",
                    repo_path=repo,
                    lockfile_path=lockfile,
                )
            )
    return pkgs


def _split_blocks(text: str) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    current_header: str | None = None
    current_body: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        if not line.startswith(" ") and line.rstrip().endswith(":"):
            if current_header is not None:
                blocks.append((current_header, current_body))
            current_header = line.rstrip()[:-1].strip()
            current_body = []
        else:
            current_body.append(line)
    if current_header is not None:
        blocks.append((current_header, current_body))
    return blocks


def _names_from_header(header: str) -> set[str]:
    # Header is one or more comma-separated `name@spec` (some may be quoted).
    out: set[str] = set()
    for raw in _split_specs(header):
        s = raw.strip().strip('"').strip("'")
        # Strip leading @ from scoped, then split on @
        if s.startswith("@"):
            at = s.find("@", 1)
            name = s[:at] if at != -1 else s
        else:
            at = s.find("@")
            name = s[:at] if at != -1 else s
        if name:
            out.add(name)
    return out


def _split_specs(header: str) -> list[str]:
    # Avoid splitting on commas inside quotes.
    parts: list[str] = []
    buf = []
    in_q: str | None = None
    for ch in header:
        if in_q:
            if ch == in_q:
                in_q = None
            buf.append(ch)
        elif ch in ('"', "'"):
            in_q = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _version_from_body(body: list[str]) -> str | None:
    for line in body:
        s = line.strip()
        if s.startswith("version:") or s.startswith('version "'):
            # `version "1.2.3"` (classic) or `version: 1.2.3` (berry)
            value = s.split(":", 1)[-1] if s.startswith("version:") else s[len("version") :]
            return value.strip().strip(":").strip().strip('"').strip("'")
    return None

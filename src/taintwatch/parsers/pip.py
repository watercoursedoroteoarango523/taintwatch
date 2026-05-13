"""pip parsers: requirements.txt (pinned only) and Pipfile.lock."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import InstalledPkg


PINNED_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^;\s#]+)")


def parse_requirements(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    pkgs: set[InstalledPkg] = set()
    for raw in lockfile.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = PINNED_RE.match(line)
        if not m:
            continue
        name, version = m.group(1), m.group(2)
        pkgs.add(
            InstalledPkg(
                ecosystem="PyPI",
                name=_canonicalize(name),
                version=version,
                source="lockfile",
                repo_path=repo,
                lockfile_path=lockfile,
            )
        )
    return pkgs


def parse_pipfile_lock(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    data = json.loads(lockfile.read_text(encoding="utf-8"))
    pkgs: set[InstalledPkg] = set()
    for section in ("default", "develop"):
        for name, entry in (data.get(section) or {}).items():
            version = entry.get("version", "")
            if isinstance(version, str) and version.startswith("=="):
                version = version[2:]
            if not version:
                continue
            pkgs.add(
                InstalledPkg(
                    ecosystem="PyPI",
                    name=_canonicalize(name),
                    version=version,
                    source="lockfile",
                    repo_path=repo,
                    lockfile_path=lockfile,
                )
            )
    return pkgs


def _canonicalize(name: str) -> str:
    # PEP 503: lowercase, collapse runs of -/_/. into a single -
    return re.sub(r"[-_.]+", "-", name).lower()

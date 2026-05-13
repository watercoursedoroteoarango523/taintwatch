"""Cargo.lock parser."""
from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

from ..models import InstalledPkg


def parse(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    with open(lockfile, "rb") as f:
        data = tomllib.load(f)
    pkgs: set[InstalledPkg] = set()
    for entry in data.get("package", []):
        name = entry.get("name")
        version = entry.get("version")
        source = entry.get("source", "")
        # Skip path-only deps (workspace members) that have no source — they're not from crates.io
        if not name or not version:
            continue
        if source and not source.startswith("registry+"):
            # git or path deps — still report; the registry+ filter would miss yanked crates
            pass
        pkgs.add(
            InstalledPkg(
                ecosystem="crates.io",
                name=name,
                version=version,
                source="lockfile",
                repo_path=repo,
                lockfile_path=lockfile,
            )
        )
    return pkgs

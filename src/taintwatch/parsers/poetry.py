"""poetry.lock parser. TOML-based, well-structured."""
from __future__ import annotations

import re
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
        if not name or not version:
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
    return re.sub(r"[-_.]+", "-", name).lower()

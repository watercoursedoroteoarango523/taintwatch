"""go.sum parser. Each line is `<module> <version> <hash>` or `<module> <version>/go.mod <hash>`."""
from __future__ import annotations

from pathlib import Path

from ..models import InstalledPkg


def parse(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    pkgs: set[InstalledPkg] = set()
    for raw in lockfile.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        module = parts[0]
        version = parts[1]
        # Strip "/go.mod" suffix from version (these lines duplicate module info)
        if version.endswith("/go.mod"):
            version = version[: -len("/go.mod")]
        pkgs.add(
            InstalledPkg(
                ecosystem="Go",
                name=module,
                version=version,
                source="lockfile",
                repo_path=repo,
                lockfile_path=lockfile,
            )
        )
    return pkgs

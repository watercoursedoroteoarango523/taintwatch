"""package-lock.json (npm) parser. Supports v1, v2, v3."""
from __future__ import annotations

import json
from pathlib import Path

from ..models import InstalledPkg


def parse(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    data = json.loads(lockfile.read_text(encoding="utf-8"))
    pkgs: set[InstalledPkg] = set()

    # v2/v3: top-level "packages" map keyed by relative path; v1: top-level "dependencies".
    if isinstance(data.get("packages"), dict):
        for key, entry in data["packages"].items():
            if not isinstance(entry, dict):
                continue
            # The root project entry has key "" and represents the consuming app, skip.
            if key == "":
                continue
            name = entry.get("name") or _name_from_path(key)
            version = entry.get("version")
            if not name or not version:
                continue
            pkgs.add(
                InstalledPkg(
                    ecosystem="npm",
                    name=name,
                    version=str(version),
                    source="lockfile",
                    repo_path=repo,
                    lockfile_path=lockfile,
                )
            )
    if isinstance(data.get("dependencies"), dict):
        _walk_v1(data["dependencies"], repo, lockfile, pkgs)
    return pkgs


def _walk_v1(deps: dict, repo: Path, lockfile: Path, out: set[InstalledPkg]) -> None:
    for name, entry in deps.items():
        if not isinstance(entry, dict):
            continue
        version = entry.get("version")
        if isinstance(version, str):
            out.add(
                InstalledPkg(
                    ecosystem="npm",
                    name=name,
                    version=version,
                    source="lockfile",
                    repo_path=repo,
                    lockfile_path=lockfile,
                )
            )
        sub = entry.get("dependencies")
        if isinstance(sub, dict):
            _walk_v1(sub, repo, lockfile, out)


def _name_from_path(key: str) -> str | None:
    # "node_modules/foo" -> "foo"
    # "node_modules/foo/node_modules/@scope/bar" -> "@scope/bar"
    parts = key.split("node_modules/")
    if not parts:
        return None
    tail = parts[-1]
    if not tail:
        return None
    # Scoped packages: "@scope/pkg" has a slash.
    if tail.startswith("@"):
        bits = tail.split("/", 2)
        if len(bits) >= 2:
            return f"{bits[0]}/{bits[1]}"
        return tail
    return tail.split("/", 1)[0]

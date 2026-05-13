"""Deep-scan walks of installed dependency directories.

We look for:
- node_modules/*/package.json and node_modules/@scope/*/package.json
- (any Python install root)/site-packages/*.dist-info/METADATA  (with -info/PKG-INFO fallback)

That covers the Shai-Hulud case: the lockfile may have been rolled back, but the
malicious package is still on disk under node_modules and would still be loaded
by `npm run`, `node`, or any tool that resolves from there.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

from .models import InstalledPkg


METADATA_NAME_RE = re.compile(r"^Name:\s*(.+)$", re.MULTILINE)
METADATA_VER_RE = re.compile(r"^Version:\s*(.+)$", re.MULTILINE)


def walk_repo(repo: Path) -> set[InstalledPkg]:
    pkgs: set[InstalledPkg] = set()
    pkgs.update(_walk_node_modules(repo))
    pkgs.update(_walk_python_site_packages(repo))
    return pkgs


def _walk_node_modules(repo: Path) -> Iterator[InstalledPkg]:
    # Walk only the top-level node_modules. Nested node_modules are also installed
    # code that could be malicious, so we walk those too — but we cap recursion
    # depth at 4 to avoid pathological cases.
    nm = repo / "node_modules"
    if not nm.is_dir():
        return
    yield from _walk_nm(nm, repo, depth=0)


def _walk_nm(nm: Path, repo: Path, depth: int) -> Iterator[InstalledPkg]:
    if depth > 4:
        return
    try:
        entries = list(nm.iterdir())
    except (PermissionError, OSError):
        return
    for entry in entries:
        if not entry.is_dir():
            continue
        name = entry.name
        if name == ".bin" or name == ".cache":
            continue
        if name.startswith("@"):
            # Scoped: iterate one more level.
            try:
                for sub in entry.iterdir():
                    if sub.is_dir():
                        yield from _emit_pkg_json(sub, repo)
                        nested = sub / "node_modules"
                        if nested.is_dir():
                            yield from _walk_nm(nested, repo, depth + 1)
            except (PermissionError, OSError):
                continue
            continue
        yield from _emit_pkg_json(entry, repo)
        nested = entry / "node_modules"
        if nested.is_dir():
            yield from _walk_nm(nested, repo, depth + 1)


def _emit_pkg_json(pkg_dir: Path, repo: Path) -> Iterator[InstalledPkg]:
    pj = pkg_dir / "package.json"
    if not pj.is_file():
        return
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return
    name = data.get("name")
    version = data.get("version")
    if not name or not version:
        return
    yield InstalledPkg(
        ecosystem="npm",
        name=name,
        version=str(version),
        source="installed",
        repo_path=repo,
        installed_path=pj,
    )


def _walk_python_site_packages(repo: Path) -> Iterator[InstalledPkg]:
    # Probe common venv layouts under the repo.
    candidates: list[Path] = []
    for venv in ("venv", ".venv", "env", ".env"):
        v = repo / venv
        if not v.is_dir():
            continue
        # Linux/Mac
        candidates.append(v / "lib")
        # Windows
        candidates.append(v / "Lib" / "site-packages")
    for c in candidates:
        if not c.exists():
            continue
        # Find every site-packages descendant (handles "lib/pythonX.Y/site-packages")
        try:
            for sp in _find_site_packages(c):
                yield from _emit_dist_info(sp, repo)
        except (PermissionError, OSError):
            continue


def _find_site_packages(start: Path) -> Iterator[Path]:
    if start.name == "site-packages" and start.is_dir():
        yield start
        return
    try:
        for entry in start.iterdir():
            if entry.is_dir():
                if entry.name == "site-packages":
                    yield entry
                else:
                    yield from _find_site_packages(entry)
    except (PermissionError, OSError):
        return


def _emit_dist_info(site_pkgs: Path, repo: Path) -> Iterator[InstalledPkg]:
    try:
        entries = list(site_pkgs.iterdir())
    except (PermissionError, OSError):
        return
    for entry in entries:
        if not entry.is_dir():
            continue
        meta_file = None
        if entry.name.endswith(".dist-info"):
            meta_file = entry / "METADATA"
        elif entry.name.endswith(".egg-info"):
            meta_file = entry / "PKG-INFO"
        else:
            continue
        if not meta_file.is_file():
            continue
        try:
            text = meta_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = METADATA_NAME_RE.search(text)
        v = METADATA_VER_RE.search(text)
        if not n or not v:
            continue
        yield InstalledPkg(
            ecosystem="PyPI",
            name=_canon_pypi(n.group(1).strip()),
            version=v.group(1).strip(),
            source="installed",
            repo_path=repo,
            installed_path=meta_file,
        )


def _canon_pypi(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()

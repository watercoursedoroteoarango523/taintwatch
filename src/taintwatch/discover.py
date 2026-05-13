"""Walk scan roots, find repos by .git/ or known lockfile presence."""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterator

from .config import Config
from .models import RepoCtx
from .parsers import LOCKFILE_PARSERS


LOCKFILE_NAMES = {name for name, _ in LOCKFILE_PARSERS}

# Hard noise: never descend into these for repo discovery. installed.py walks
# node_modules/site-packages separately so we don't lose deep-scan coverage.
NOISE_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "target",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cargo",
    ".gradle",
    "obj",
    "bin",
    ".idea",
    ".vscode",
}


def _matches_any(path: Path, globs: list[str]) -> bool:
    s = path.as_posix()
    return any(fnmatch.fnmatch(s, g) for g in globs)


def discover_repos(cfg: Config) -> Iterator[RepoCtx]:
    """Yield one RepoCtx per discovered repo across all roots."""
    for root in cfg.scan.roots:
        if not root.exists():
            continue
        yield from _walk(root, cfg.scan.excludes)


def _walk(root: Path, excludes: list[str]) -> Iterator[RepoCtx]:
    # We treat any directory that contains .git/ OR a known lockfile at its top level
    # as a repo. After yielding a repo, we KEEP descending — submodules / nested workspaces
    # are reported separately so their lockfiles are picked up.
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        lockfiles: list[Path] = []
        has_git = False
        for e in entries:
            if e.is_dir():
                if e.name in NOISE_DIRS:
                    if e.name == ".git":
                        has_git = True
                    continue
                if _matches_any(e, excludes):
                    continue
                stack.append(e)
            else:
                if e.name in LOCKFILE_NAMES:
                    if _matches_any(e, excludes):
                        continue
                    lockfiles.append(e)
        if has_git or lockfiles:
            # If a directory has only a sub-lockfile (no .git, no top-level lockfile),
            # we still want to scan that sub. The recursive walk above handles it because
            # we descend into every non-noise directory.
            if lockfiles:
                yield RepoCtx(path=current, lockfiles=lockfiles)

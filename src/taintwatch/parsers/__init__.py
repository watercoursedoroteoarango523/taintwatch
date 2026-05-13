from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..models import InstalledPkg
from . import cargo, gomod, npm, pip, pnpm, poetry, yarn


# Order matters: pnpm-lock.yaml takes precedence over package-lock.json,
# and Pipfile.lock over requirements.txt for the same project.
LOCKFILE_PARSERS: tuple[tuple[str, Callable[[Path, Path], set[InstalledPkg]]], ...] = (
    ("pnpm-lock.yaml", pnpm.parse),
    ("yarn.lock", yarn.parse),
    ("package-lock.json", npm.parse),
    ("Pipfile.lock", pip.parse_pipfile_lock),
    ("poetry.lock", poetry.parse),
    ("requirements.txt", pip.parse_requirements),
    ("Cargo.lock", cargo.parse),
    ("go.sum", gomod.parse),
)


def parse_all(repo: Path, lockfiles: list[Path]) -> set[InstalledPkg]:
    """Run every applicable parser on a repo's lockfiles."""
    pkgs: set[InstalledPkg] = set()
    seen_kinds: set[str] = set()
    for lf in lockfiles:
        name = lf.name
        for kind, parser in LOCKFILE_PARSERS:
            if name == kind:
                # Skip requirements.txt if Pipfile.lock or poetry.lock already produced PyPI data
                if kind == "requirements.txt" and "Pipfile.lock" in seen_kinds:
                    break
                try:
                    pkgs.update(parser(lf, repo))
                    seen_kinds.add(kind)
                except Exception:
                    # Best-effort: a malformed lockfile shouldn't abort the whole scan.
                    pass
                break
    return pkgs

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ECOSYSTEMS = ("npm", "PyPI", "crates.io", "Go", "RubyGems")
ECOSYSTEM_ALIASES = {
    "npm": "npm",
    "pypi": "PyPI",
    "PyPI": "PyPI",
    "cargo": "crates.io",
    "crates.io": "crates.io",
    "go": "Go",
    "Go": "Go",
    "rubygems": "RubyGems",
    "RubyGems": "RubyGems",
}


def canonical_ecosystem(value: str) -> str:
    return ECOSYSTEM_ALIASES.get(value, value)


@dataclass(frozen=True)
class InstalledPkg:
    ecosystem: str
    name: str
    version: str
    source: str  # "lockfile" | "installed"
    repo_path: Path
    lockfile_path: Path | None = None
    installed_path: Path | None = None


@dataclass
class AffectedRange:
    """Subset of OSV `ranges` semantics that we care about."""

    type: str  # "SEMVER" | "ECOSYSTEM" | "GIT"
    introduced: str | None = None
    fixed: str | None = None
    last_affected: str | None = None


@dataclass
class Advisory:
    id: str
    ecosystem: str
    name: str
    summary: str = ""
    severity: str = ""
    source: str = ""  # "osv" | "openssf" | "aikido"
    versions: list[str] = field(default_factory=list)  # explicit affected versions
    ranges: list[AffectedRange] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hit:
    advisory_id: str
    advisory: Advisory
    pkg: InstalledPkg
    is_new: bool = True


@dataclass
class RepoCtx:
    path: Path
    lockfiles: list[Path] = field(default_factory=list)

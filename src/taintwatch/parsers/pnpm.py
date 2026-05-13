"""pnpm-lock.yaml parser.

Avoids a YAML dep by parsing the line-based structure of pnpm lockfiles directly.
Format references:
  v5/v6/v9 all use a top-level `packages:` map whose keys are
  `/<name>@<version>` (older) or `'@<scope>/<name>@<version>(peer-deps)'` (newer).
"""
from __future__ import annotations

import re
from pathlib import Path

from ..models import InstalledPkg


# Match the package key after `packages:` block.
KEY_RE = re.compile(
    r"""
    ^['"]?                              # optional quote
    /?                                  # optional leading slash (v5/v6)
    (?P<name>@?[^/@'"\s]+(?:/[^@/'"\s]+)?)   # name or @scope/name
    @                                   # separator
    (?P<version>[^()'"\s]+)             # version up to ( or quote/space
    """,
    re.VERBOSE,
)


def parse(lockfile: Path, repo: Path) -> set[InstalledPkg]:
    pkgs: set[InstalledPkg] = set()
    text = lockfile.read_text(encoding="utf-8")
    in_packages = False
    for raw in text.splitlines():
        line = raw.rstrip("\n").rstrip()
        if not line:
            continue
        if not line.startswith(" "):
            in_packages = line.strip().rstrip(":") == "packages"
            continue
        if not in_packages:
            continue
        # Top-level package key: indented exactly 2 spaces, ends with `:`
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            key = line.strip().rstrip(":").strip()
            m = KEY_RE.match(key)
            if not m:
                continue
            name = m.group("name")
            version = m.group("version")
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

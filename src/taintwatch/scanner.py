"""Match installed packages against the advisory DB."""
from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path

from .config import Config
from .discover import discover_repos
from .installed import walk_repo
from .models import Hit, InstalledPkg, RepoCtx, canonical_ecosystem
from .parsers import parse_all
from .state import (
    advisories_for,
    finish_scan_run,
    get_lockfile_cache,
    hits_for_run,
    insert_hits,
    last_completed_run,
    set_lockfile_cache,
    start_scan_run,
)
from .version_match import is_affected


def _pkgs_to_json(pkgs: set[InstalledPkg]) -> str:
    return json.dumps(
        [
            {
                "ecosystem": p.ecosystem,
                "name": p.name,
                "version": p.version,
                "source": p.source,
                "lockfile": str(p.lockfile_path) if p.lockfile_path else None,
                "installed": str(p.installed_path) if p.installed_path else None,
            }
            for p in pkgs
        ]
    )


def _pkgs_from_json(s: str, repo: Path) -> set[InstalledPkg]:
    out: set[InstalledPkg] = set()
    for item in json.loads(s):
        out.add(
            InstalledPkg(
                ecosystem=item["ecosystem"],
                name=item["name"],
                version=item["version"],
                source=item["source"],
                repo_path=repo,
                lockfile_path=Path(item["lockfile"]) if item.get("lockfile") else None,
                installed_path=Path(item["installed"]) if item.get("installed") else None,
            )
        )
    return out


def _gather_pkgs(conn: sqlite3.Connection, repo: RepoCtx, deep: bool) -> set[InstalledPkg]:
    """Return the (cached-when-possible) set of installed packages for one repo."""
    if not repo.lockfiles:
        if deep:
            return walk_repo(repo.path)
        return set()
    # Use mtime of newest lockfile as the cache key for the whole repo.
    newest_mtime = max((lf.stat().st_mtime_ns for lf in repo.lockfiles), default=0)
    cache_key_path = "|".join(sorted(lf.as_posix() for lf in repo.lockfiles))
    cached = get_lockfile_cache(conn, str(repo.path), cache_key_path)
    if cached is not None and cached[0] == newest_mtime:
        pkgs = _pkgs_from_json(cached[1], repo.path)
    else:
        pkgs = parse_all(repo.path, repo.lockfiles)
        set_lockfile_cache(
            conn, str(repo.path), cache_key_path, newest_mtime, _pkgs_to_json(pkgs)
        )
    if deep:
        pkgs.update(walk_repo(repo.path))
    return pkgs


def _match(conn: sqlite3.Connection, pkgs: Iterable[InstalledPkg]) -> list[Hit]:
    """Match installed packages against the advisory DB.

    A single physical hit may appear many times (e.g. @mistralai/mistralai is
    installed under N nested node_modules paths AND listed in package-lock.json).
    For alerting and reporting, the user cares about one finding per
    (advisory, repo, version) — pick a canonical representative (preferring
    lockfile source so the alert points at the file the user edits).
    """
    hits_by_key: dict[tuple[str, str, str], Hit] = {}
    cache: dict[tuple[str, str], list] = {}
    for pkg in pkgs:
        eco = canonical_ecosystem(pkg.ecosystem)
        key_eco_name = (eco, pkg.name)
        if key_eco_name not in cache:
            cache[key_eco_name] = advisories_for(conn, eco, pkg.name)
        for adv in cache[key_eco_name]:
            if not is_affected(pkg.version, adv):
                continue
            dedupe_key = (adv.id, str(pkg.repo_path), pkg.version)
            existing = hits_by_key.get(dedupe_key)
            if existing is None:
                hits_by_key[dedupe_key] = Hit(advisory_id=adv.id, advisory=adv, pkg=pkg)
            elif pkg.source == "lockfile" and existing.pkg.source != "lockfile":
                # Prefer lockfile over installed for the canonical representative.
                hits_by_key[dedupe_key] = Hit(advisory_id=adv.id, advisory=adv, pkg=pkg)
    return list(hits_by_key.values())


def run_scan(conn: sqlite3.Connection, cfg: Config) -> tuple[int, list[Hit], set[tuple[str, str, str]]]:
    """Run one scan cycle. Returns (run_id, all_hits, new_hit_keys)."""
    prior_run = last_completed_run(conn)
    prior_keys: set[tuple[str, str, str]] = set(hits_for_run(conn, prior_run)) if prior_run else set()

    run_id = start_scan_run(conn)
    all_hits: list[Hit] = []
    repos_scanned = 0
    for repo in discover_repos(cfg):
        repos_scanned += 1
        pkgs = _gather_pkgs(conn, repo, cfg.scan.deep_scan)
        if not pkgs:
            continue
        all_hits.extend(_match(conn, pkgs))

    # Annotate "new this run" based on prior_keys.
    new_keys: set[tuple[str, str, str]] = set()
    for h in all_hits:
        key = (h.advisory_id, str(h.pkg.repo_path), h.pkg.version)
        if key not in prior_keys:
            new_keys.add(key)
            h.is_new = True
        else:
            h.is_new = False

    insert_hits(conn, run_id, all_hits)
    finish_scan_run(conn, run_id, repos_scanned, len(all_hits))
    return run_id, all_hits, new_keys

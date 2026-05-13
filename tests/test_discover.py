from __future__ import annotations

from pathlib import Path

from taintwatch.config import Config, ScanConfig
from taintwatch.discover import discover_repos


def test_discovers_repos_with_lockfiles(tmp_path: Path):
    root = tmp_path / "code"
    root.mkdir()
    a = root / "appA"
    b = root / "appB"
    a.mkdir()
    b.mkdir()
    (a / "package-lock.json").write_text("{}")
    (b / "Cargo.lock").write_text("version = 3")
    # noise dir
    (a / "node_modules").mkdir()
    (a / "node_modules" / "package-lock.json").write_text("{}")

    cfg = Config(scan=ScanConfig(roots=[root]))
    repos = list(discover_repos(cfg))
    paths = sorted(r.path.name for r in repos)
    assert "appA" in paths
    assert "appB" in paths
    # node_modules should not yield a repo
    for r in repos:
        assert "node_modules" not in str(r.path)


def test_excludes_match(tmp_path: Path):
    root = tmp_path / "code"
    root.mkdir()
    (root / "old" / "app").mkdir(parents=True)
    (root / "old" / "app" / "package-lock.json").write_text("{}")
    (root / "live" / "app").mkdir(parents=True)
    (root / "live" / "app" / "package-lock.json").write_text("{}")

    cfg = Config(scan=ScanConfig(roots=[root], excludes=["**/old/**"]))
    repos = list(discover_repos(cfg))
    paths = [r.path.as_posix() for r in repos]
    assert any("/live/app" in p for p in paths)
    assert all("/old/" not in p for p in paths)

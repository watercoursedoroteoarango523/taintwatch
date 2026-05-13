"""End-to-end: a fixture repo with chalk@5.6.1 pinned + an advisory in the DB,
expect exactly one hit and an alert dispatched to stdout."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from taintwatch.alerts import dispatch_new_hits
from taintwatch.config import (
    AlertsConfig,
    Config,
    DaemonConfig,
    DiscordAlertConfig,
    FeedsConfig,
    ReportAlertConfig,
    ScanConfig,
    ToastAlertConfig,
)
from taintwatch.models import Advisory
from taintwatch.scanner import run_scan
from taintwatch.state import open_db, upsert_advisory


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "myapp"
    repo.mkdir()
    # Pretend it's a real git repo
    (repo / ".git").mkdir()
    src = Path(__file__).parent / "fixtures" / "lockfiles" / "package-lock.json"
    shutil.copy(src, repo / "package-lock.json")
    return repo


def _cfg(roots: list[Path], db_path: Path) -> Config:
    # We disable real feeds for the test; advisories are seeded directly.
    return Config(
        scan=ScanConfig(roots=roots, deep_scan=False),
        feeds=FeedsConfig(osv=False, openssf=False, aikido=False),
        alerts=AlertsConfig(
            discord=DiscordAlertConfig(webhook=""),
            toast=ToastAlertConfig(enabled=False),
            report=ReportAlertConfig(dir=db_path.parent / "reports"),
        ),
        daemon=DaemonConfig(),
    )


def test_chalk_5_6_1_is_detected(tmp_path: Path, fixture_repo: Path, mocker):
    # Pin DB to tmp_path to avoid clobbering the real user state
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "state.db")
    cfg = _cfg([fixture_repo.parent], tmp_path)

    with open_db() as conn:
        upsert_advisory(
            conn,
            Advisory(
                id="MAL-2025-CHALK-FAKE",
                ecosystem="npm",
                name="chalk",
                summary="Test advisory for chalk 5.6.1",
                severity="HIGH",
                source="osv",
                versions=["5.6.1"],
                ranges=[],
                references=["https://example.test/MAL-2025-CHALK-FAKE"],
            ),
        )
        run_id, all_hits, new_keys = run_scan(conn, cfg)

    assert run_id >= 1
    names = [(h.pkg.name, h.pkg.version, h.advisory_id) for h in all_hits]
    assert ("chalk", "5.6.1", "MAL-2025-CHALK-FAKE") in names
    # Exactly one chalk hit (parser-emitted)
    chalk_hits = [h for h in all_hits if h.pkg.name == "chalk"]
    assert len(chalk_hits) == 1
    assert chalk_hits[0].is_new is True


def test_diff_does_not_re_alert_on_unchanged_run(tmp_path: Path, fixture_repo: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "state.db")
    cfg = _cfg([fixture_repo.parent], tmp_path)

    with open_db() as conn:
        upsert_advisory(
            conn,
            Advisory(
                id="MAL-X",
                ecosystem="npm",
                name="chalk",
                source="osv",
                versions=["5.6.1"],
            ),
        )
        # Scan 1
        _, hits1, new1 = run_scan(conn, cfg)
        counts1 = dispatch_new_hits(conn, cfg, hits1, new1)
        assert counts1.get("stdout", 0) == 1

        # Scan 2 — same state, alert should not refire
        _, hits2, new2 = run_scan(conn, cfg)
        counts2 = dispatch_new_hits(conn, cfg, hits2, new2)
        # is_new should now be False for the same hit, AND alert_log dedupes
        assert counts2.get("stdout", 0) == 0


def test_lockfile_cache_hit_skips_reparse(tmp_path: Path, fixture_repo: Path, mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_path / "state.db")
    cfg = _cfg([fixture_repo.parent], tmp_path)

    parse_calls = []
    import taintwatch.scanner as scanner_mod

    original_parse_all = scanner_mod.parse_all

    def counting_parse(*a, **kw):
        parse_calls.append(1)
        return original_parse_all(*a, **kw)

    mocker.patch.object(scanner_mod, "parse_all", side_effect=counting_parse)

    with open_db() as conn:
        run_scan(conn, cfg)
        run_scan(conn, cfg)

    # First scan parses; second should hit the lockfile cache (mtime unchanged)
    assert len(parse_calls) == 1

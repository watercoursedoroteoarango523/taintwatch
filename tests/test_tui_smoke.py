"""Headless smoke tests for the TUI — verify each screen composes and
navigation keybindings work. Uses Textual's `App.run_test` pilot so we
never need a real terminal.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_home_screen_loads(mocker):
    import tempfile
    from pathlib import Path

    tmp_root = Path(tempfile.mkdtemp())
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp_root / "state.db")
    # Pre-create the first-launch marker so the welcome modal doesn't appear
    # on top of HomeScreen during the test. The TUI's own logic touches this
    # file the first time it boots.
    marker = tmp_root / "first-launch-seen"
    marker.touch()
    mocker.patch("taintwatch.paths.first_launch_marker", return_value=marker)
    # Seed feed rows so the auto-refresh worker doesn't fire and try to hit
    # the real network during the test.
    import time as _time

    from taintwatch.state import open_db, set_feed_status
    with open_db() as conn:
        for name in ("osv", "openssf", "aikido"):
            set_feed_status(conn, name, etag=None, status="ok")
            conn.execute(
                "UPDATE feeds SET last_fetched = ? WHERE name = ?",
                (int(_time.time()), name),
            )

    from taintwatch.tui import (
        FeedsScreen,
        HitsScreen,
        HomeScreen,
        TaintwatchApp,
    )

    app = TaintwatchApp()
    async with app.run_test() as pilot:
        assert isinstance(app.screen, HomeScreen)

        await pilot.press("f")
        await pilot.pause()
        assert isinstance(app.screen, FeedsScreen)

        await pilot.press("q")
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)

        await pilot.press("h")
        await pilot.pause()
        assert isinstance(app.screen, HitsScreen)

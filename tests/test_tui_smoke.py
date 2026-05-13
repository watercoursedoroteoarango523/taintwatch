"""Headless smoke tests for the TUI — verify each screen composes and
navigation keybindings work. Uses Textual's `App.run_test` pilot so we
never need a real terminal.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_home_screen_loads(mocker):
    mocker.patch("taintwatch.paths.state_db_path", return_value=mocker.MagicMock())
    # Use a real tmp DB to keep state.open_db happy.
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp()) / "state.db"
    mocker.patch("taintwatch.paths.state_db_path", return_value=tmp)

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

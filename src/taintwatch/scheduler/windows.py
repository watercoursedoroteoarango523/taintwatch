"""Windows Task Scheduler integration via schtasks.exe."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .base import Scheduler

TASK_NAME = "taintwatch"


def _exe() -> str:
    # Prefer the resolved entry point. Falls back to `python -m taintwatch.cli`.
    cand = shutil.which("taintwatch")
    if cand:
        return cand
    return f'"{sys.executable}" -m taintwatch.cli'


class WindowsScheduler(Scheduler):
    def install(self, interval_minutes: int, *, dry_run: bool = False) -> str:
        # schtasks supports MI (modifier) for /SC MINUTE up to 1439.
        interval = max(1, min(1439, interval_minutes))
        action = f'{_exe()} scan'
        cmd = [
            "schtasks",
            "/Create",
            "/F",
            "/SC",
            "MINUTE",
            "/MO",
            str(interval),
            "/TN",
            TASK_NAME,
            "/TR",
            action,
            "/RL",
            "LIMITED",
        ]
        if dry_run:
            return " ".join(cmd)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"schtasks failed: {r.stderr.strip() or r.stdout.strip()}")
        return f"installed Windows Task Scheduler job '{TASK_NAME}' every {interval} minutes"

    def uninstall(self) -> str:
        r = subprocess.run(
            ["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return f"no '{TASK_NAME}' job present (or schtasks said: {r.stderr.strip()})"
        return f"removed Windows Task Scheduler job '{TASK_NAME}'"

    def status(self) -> str:
        r = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return "not installed"
        return r.stdout

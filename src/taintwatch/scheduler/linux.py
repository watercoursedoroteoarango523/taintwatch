"""Linux systemd user service + timer."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .base import Scheduler

SERVICE = "taintwatch.service"
TIMER = "taintwatch.timer"


def _exe() -> str:
    cand = shutil.which("taintwatch")
    if cand:
        return cand
    return f"{sys.executable} -m taintwatch.cli"


def _unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


class LinuxScheduler(Scheduler):
    def install(self, interval_minutes: int, *, dry_run: bool = False) -> str:
        exe = _exe()
        service_text = f"""[Unit]
Description=taintwatch — scan for compromised package versions

[Service]
Type=oneshot
ExecStart={exe} scan
"""
        timer_text = f"""[Unit]
Description=Run taintwatch every {interval_minutes}m

[Timer]
OnBootSec=2m
OnUnitActiveSec={interval_minutes}m
Persistent=true

[Install]
WantedBy=timers.target
"""
        ud = _unit_dir()
        if dry_run:
            return (
                f"# would write {ud / SERVICE}\n{service_text}\n"
                f"# would write {ud / TIMER}\n{timer_text}"
            )
        ud.mkdir(parents=True, exist_ok=True)
        (ud / SERVICE).write_text(service_text, encoding="utf-8")
        (ud / TIMER).write_text(timer_text, encoding="utf-8")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", TIMER],
            check=True,
        )
        return f"installed systemd user timer (every {interval_minutes}m)"

    def uninstall(self) -> str:
        ud = _unit_dir()
        subprocess.run(["systemctl", "--user", "disable", "--now", TIMER], capture_output=True)
        for f in (SERVICE, TIMER):
            p = ud / f
            if p.exists():
                p.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        return "removed systemd user units"

    def status(self) -> str:
        r = subprocess.run(
            ["systemctl", "--user", "status", TIMER],
            capture_output=True,
            text=True,
        )
        return r.stdout or r.stderr or "(no status)"

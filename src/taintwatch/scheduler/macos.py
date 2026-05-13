"""macOS launchd LaunchAgent."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .base import Scheduler

LABEL = "dev.taintwatch"


def _exe() -> str:
    cand = shutil.which("taintwatch")
    if cand:
        return cand
    return sys.executable


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _plist(interval_seconds: int) -> str:
    exe = _exe()
    args_xml = ""
    if exe == sys.executable:
        args_xml = "<string>-m</string><string>taintwatch.cli</string>"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{exe}</string>
    {args_xml}
    <string>scan</string>
  </array>
  <key>StartInterval</key><integer>{interval_seconds}</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>/tmp/taintwatch.out.log</string>
  <key>StandardErrorPath</key><string>/tmp/taintwatch.err.log</string>
</dict>
</plist>
"""


class MacosScheduler(Scheduler):
    def install(self, interval_minutes: int, *, dry_run: bool = False) -> str:
        p = _plist_path()
        plist_text = _plist(max(60, interval_minutes * 60))
        if dry_run:
            return f"# would write {p}\n{plist_text}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(plist_text, encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
        subprocess.run(["launchctl", "load", str(p)], capture_output=True, check=True)
        return f"installed LaunchAgent {p} every {interval_minutes}m"

    def uninstall(self) -> str:
        p = _plist_path()
        if not p.exists():
            return "no LaunchAgent installed"
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
        p.unlink()
        return f"removed LaunchAgent {p}"

    def status(self) -> str:
        p = _plist_path()
        if not p.exists():
            return "not installed"
        r = subprocess.run(["launchctl", "list", LABEL], capture_output=True, text=True)
        return r.stdout or r.stderr or "(no status)"

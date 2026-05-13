"""Native desktop toast notifications. Best-effort, swallows failures silently."""
from __future__ import annotations

import shutil
import subprocess
import sys

from ..models import Hit
from .base import AlertChannel


class ToastChannel(AlertChannel):
    name = "toast"

    def send(self, hits: list[Hit]) -> None:
        if not hits:
            return
        title = "taintwatch: compromised packages"
        if len(hits) == 1:
            h = hits[0]
            body = f"{h.pkg.name}@{h.pkg.version} in {h.pkg.repo_path.name} ({h.advisory_id})"
        else:
            body = f"{len(hits)} new hit(s) across your repos. Open the report."
        _toast(title, body)


def _toast(title: str, body: str) -> None:
    try:
        if sys.platform == "win32":
            try:
                from winotify import Notification  # type: ignore
            except ImportError:
                return
            n = Notification(app_id="taintwatch", title=title, msg=body, duration="long")
            n.show()
        elif sys.platform == "darwin":
            # Use osascript — no extra dep
            script = f'display notification "{_esc(body)}" with title "{_esc(title)}"'
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            if shutil.which("notify-send"):
                subprocess.run(
                    ["notify-send", title, body],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception:
        return


def _esc(s: str) -> str:
    return s.replace('"', "'")

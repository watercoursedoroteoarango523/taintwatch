"""Native desktop toast notifications with three escalating sound tiers.

Sound by severity:

| Severity | Windows (winotify)      | macOS (osascript sound) | Linux (paplay sound file)                                       |
|----------|-------------------------|-------------------------|-----------------------------------------------------------------|
| CRITICAL | LoopingAlarm (loops)    | Sosumi                  | freedesktop/dialog-warning.oga                                  |
| HIGH     | Default                 | Glass                   | freedesktop/message-new-instant.oga                             |
| INFO     | Reminder (short)        | Tink                    | freedesktop/complete.oga                                        |

If a sound file or named sound isn't available, the OS falls back to its own
default and we keep going — toast delivery is best-effort.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

from ..models import Hit
from .base import AlertChannel
from .severity import Severity


# Linux: paplay/aplay sound file candidates per severity.
# Different distros ship sounds in different places; try them in order.
_LINUX_SOUND_CANDIDATES = {
    Severity.CRITICAL: [
        "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
        "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
        "/usr/share/sounds/ubuntu/stereo/dialog-warning.ogg",
    ],
    Severity.HIGH: [
        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/ubuntu/stereo/message.ogg",
    ],
    Severity.INFO: [
        "/usr/share/sounds/freedesktop/stereo/complete.oga",
        "/usr/share/sounds/freedesktop/stereo/dialog-information.oga",
    ],
}


class ToastChannel(AlertChannel):
    name = "toast"

    def send(self, hits: list[Hit], severity: Severity = Severity.HIGH) -> None:
        if not hits:
            return
        title = _title_for(severity)
        if len(hits) == 1:
            h = hits[0]
            where = "ON DISK" if h.pkg.source == "installed" else "in lockfile"
            body = f"{h.pkg.name}@{h.pkg.version} {where} — {h.pkg.repo_path.name} ({h.advisory_id})"
        else:
            installed_count = sum(1 for h in hits if h.pkg.source == "installed")
            if installed_count:
                body = f"{len(hits)} hits — {installed_count} INSTALLED ON DISK. Open the report."
            else:
                body = f"{len(hits)} hits across your repos. Open the report."
        _toast(title, body, severity)


def _title_for(severity: Severity) -> str:
    if severity is Severity.CRITICAL:
        return "taintwatch: CRITICAL — compromised code installed"
    if severity is Severity.HIGH:
        return "taintwatch: compromised package in lockfile"
    return "taintwatch"


def _toast(title: str, body: str, severity: Severity) -> None:
    try:
        if sys.platform == "win32":
            _toast_windows(title, body, severity)
        elif sys.platform == "darwin":
            _toast_macos(title, body, severity)
        else:
            _toast_linux(title, body, severity)
    except Exception:
        return


def _toast_windows(title: str, body: str, severity: Severity) -> None:
    try:
        from winotify import Notification, audio  # type: ignore
    except ImportError:
        return

    if severity is Severity.CRITICAL:
        sound = audio.Sound(audio.LoopingAlarm.c, audio.LoopingAlarm.loop)
        duration = "long"
    elif severity is Severity.HIGH:
        sound = audio.Sound(audio.Default.c, audio.Default.loop)
        duration = "long"
    else:
        sound = audio.Sound(audio.Reminder.c, audio.Reminder.loop)
        duration = "short"

    n = Notification(app_id="taintwatch", title=title, msg=body, duration=duration)
    n.set_audio(sound, loop=(severity is Severity.CRITICAL))
    n.show()


def _toast_macos(title: str, body: str, severity: Severity) -> None:
    sound = {
        Severity.CRITICAL: "Sosumi",
        Severity.HIGH: "Glass",
        Severity.INFO: "Tink",
    }[severity]
    script = (
        f'display notification "{_esc(body)}" with title "{_esc(title)}" '
        f'sound name "{sound}"'
    )
    subprocess.run(
        ["osascript", "-e", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _toast_linux(title: str, body: str, severity: Severity) -> None:
    if shutil.which("notify-send"):
        urgency = {
            Severity.CRITICAL: "critical",
            Severity.HIGH: "normal",
            Severity.INFO: "low",
        }[severity]
        subprocess.run(
            ["notify-send", f"--urgency={urgency}", title, body],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    # Sound (independent of notify-send because it doesn't reliably play sounds).
    sound_player = shutil.which("paplay") or shutil.which("aplay")
    if not sound_player:
        return
    for candidate in _LINUX_SOUND_CANDIDATES.get(severity, []):
        from pathlib import Path
        if Path(candidate).is_file():
            subprocess.Popen(
                [sound_player, candidate],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break


def _esc(s: str) -> str:
    return s.replace('"', "'").replace("\\", "\\\\")

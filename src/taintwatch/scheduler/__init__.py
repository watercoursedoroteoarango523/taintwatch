from __future__ import annotations

import sys

from .base import Scheduler


def get() -> Scheduler:
    if sys.platform == "win32":
        from . import windows
        return windows.WindowsScheduler()
    if sys.platform == "darwin":
        from . import macos
        return macos.MacosScheduler()
    from . import linux
    return linux.LinuxScheduler()

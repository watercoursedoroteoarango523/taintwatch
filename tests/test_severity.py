from __future__ import annotations

from pathlib import Path

import pytest

from taintwatch.alerts.severity import Severity, classify
from taintwatch.models import Advisory, Hit, InstalledPkg


def _hit(source: str, repo_path: str = "/tmp/repo") -> Hit:
    pkg = InstalledPkg(
        ecosystem="npm",
        name="example",
        version="1.0.0",
        source=source,
        repo_path=Path(repo_path),
        lockfile_path=Path(repo_path) / "package-lock.json" if source == "lockfile" else None,
        installed_path=Path(repo_path) / "node_modules/example/package.json" if source == "installed" else None,
    )
    adv = Advisory(id="MAL-X", ecosystem="npm", name="example", source="osv", versions=["1.0.0"])
    return Hit(advisory_id="MAL-X", advisory=adv, pkg=pkg)


def test_classify_empty_is_info():
    assert classify([]) is Severity.INFO


def test_classify_lockfile_only_is_high():
    hits = [_hit("lockfile"), _hit("lockfile")]
    assert classify(hits) is Severity.HIGH


def test_classify_any_installed_is_critical():
    hits = [_hit("lockfile"), _hit("installed")]
    assert classify(hits) is Severity.CRITICAL


def test_classify_all_installed_is_critical():
    hits = [_hit("installed"), _hit("installed")]
    assert classify(hits) is Severity.CRITICAL


def test_toast_picks_severity_specific_sound_on_windows(monkeypatch):
    """Smoke test: ToastChannel.send dispatches the right sound constant to winotify."""
    import sys

    if sys.platform != "win32":
        pytest.skip("Windows-specific sound test")

    captured = {}

    class _FakeAudio:
        class _AudioConst:
            def __init__(self, name):
                self.c = name           # winotify constants expose .c and .loop
                self.loop = "false"

        Default = _AudioConst("Default")
        LoopingAlarm = _AudioConst("LoopingAlarm")
        Reminder = _AudioConst("Reminder")

        class Sound:  # type: ignore[no-redef]
            def __init__(self, c, loop):
                self.c = c
                self.loop = loop

    class _FakeNotification:
        def __init__(self, app_id, title, msg, duration):
            captured["title"] = title
            captured["msg"] = msg
            captured["duration"] = duration

        def set_audio(self, sound, loop):
            captured["sound"] = sound
            captured["loop_flag"] = loop

        def show(self):
            captured["shown"] = True

    fake = type(sys)("winotify")
    fake.Notification = _FakeNotification
    fake.audio = _FakeAudio
    monkeypatch.setitem(sys.modules, "winotify", fake)

    from taintwatch.alerts.toast import ToastChannel

    h_installed = _hit("installed", repo_path="C:/code/myapp")
    h_lockfile = _hit("lockfile", repo_path="C:/code/myapp")

    ch = ToastChannel()
    ch.send([h_installed], Severity.CRITICAL)
    assert captured["shown"] is True
    assert captured["loop_flag"] is True

    captured.clear()
    ch.send([h_lockfile], Severity.HIGH)
    assert captured["loop_flag"] is False

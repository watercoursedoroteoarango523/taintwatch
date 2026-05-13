# `taintwatch install-autostart` / `uninstall-autostart` / `autostart-status`

Manage a per-OS scheduler entry that runs `taintwatch scan` automatically. **Opt-in.** Nothing autostarts unless you run `install-autostart` (or accept the first-launch TUI prompt).

## Per-OS implementation

| OS | What gets installed | Where |
|---|---|---|
| **Windows** | Task Scheduler job named `taintwatch` | `schtasks` |
| **macOS** | LaunchAgent | `~/Library/LaunchAgents/dev.taintwatch.plist` |
| **Linux** | systemd user timer + service | `~/.config/systemd/user/taintwatch.{timer,service}` |

In all three cases the registered action is `taintwatch scan` — a one-shot scan-and-exit. There is no long-lived service.

## `taintwatch install-autostart`

### Synopsis

```sh
taintwatch install-autostart [--interval N] [--dry-run]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--interval N` | 60 | Minutes between runs. Windows allows 1–1439. |
| `--dry-run` | off | Print the generated Task XML / plist / unit text instead of installing. Useful for review. |

### Examples

Daily scan (recommended):

```sh
taintwatch install-autostart --interval 1440
```

Hourly:

```sh
taintwatch install-autostart --interval 60
```

Inspect what would be installed without touching the system:

```sh
taintwatch install-autostart --interval 60 --dry-run
```

## `taintwatch uninstall-autostart`

### Synopsis

```sh
taintwatch uninstall-autostart
```

Removes the scheduler entry. Safe to run when nothing is installed (no-ops).

## `taintwatch autostart-status`

### Synopsis

```sh
taintwatch autostart-status
```

Prints `schtasks /Query`, `launchctl list dev.taintwatch`, or `systemctl --user status taintwatch.timer` output respectively. Useful for confirming the schedule is what you expect.

## Why scheduled `scan` and not a long-lived daemon

A scheduled one-shot survives laptop sleep / resume, OS upgrades, and your own forgetfulness about leaving a terminal open. A daemon would have to track all of that and re-run missed jobs anyway. The scheduler primitives on every supported OS already do this correctly with `Persistent=true` / `RunOnLastIfMissed` / etc.

## See also

- [commands/scan.md](scan.md) — what gets run on each tick
- [tui.md](../tui.md#first-launch-prompt) — the TUI offers this on first launch

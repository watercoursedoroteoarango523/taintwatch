# Configuration

taintwatch reads a single TOML config file. Generate one with `taintwatch config init`, locate it with `taintwatch config path`.

## File location

- **Windows** `%APPDATA%\taintwatch\config.toml`
- **macOS** `~/Library/Application Support/taintwatch/config.toml`
- **Linux** `~/.config/taintwatch/config.toml`

## Full reference

```toml
[scan]
roots = ["~/code"]                       # directories to walk for repos
excludes = []                            # extra glob patterns to skip
deep_scan = true                         # also walk node_modules / site-packages
ecosystems = ["npm", "pypi", "cargo", "go", "rubygems"]

[feeds]
osv = true                               # OSV.dev MAL-* records (recommended)
openssf = true                           # OpenSSF malicious-packages archive
aikido = true                            # Aikido Intel real-time signal
refresh_minutes = 30                     # daemon polling cadence (used by `watch`)
max_age_hours = 24                       # auto-refresh on TUI launch if older

[alerts.discord]
webhook = ""                             # paste a Discord webhook URL to enable

[alerts.toast]
enabled = true

[alerts.report]
dir = ""                                 # empty = <state_dir>/reports

[daemon]
interval_minutes = 60                    # used by `watch` and `install-autostart`
```

## `[scan]`

### `roots`

Absolute or `~`-expandable paths to walk. taintwatch discovers a repo by the presence of `.git/` or any known lockfile inside a directory. Default is `["~/code"]` — change this to match your actual layout.

You can override at the command line: `taintwatch scan --root ~/work --root ~/personal`.

### `excludes`

Extra glob patterns matched against the full path. Use POSIX-style forward slashes even on Windows. Examples:

```toml
excludes = [
    "**/old/**",
    "**/_archived/**",
    "**/tests/fixtures/**",          # exclude your own test fixtures
]
```

A hard-coded noise list always skips: `.git`, `node_modules`, `vendor`, `target`, `dist`, `build`, `.next`, `__pycache__`, `.venv`, `venv`, `.tox`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.cargo`, `.gradle`, `obj`, `bin`, `.idea`, `.vscode`. (Note: `node_modules` and `site-packages` are walked separately by the deep-scan code path — they're skipped for *repo discovery*, not for *installed-package scanning*.)

### `deep_scan`

When true (default), taintwatch also walks every repo's `node_modules/` and `*/site-packages/*.dist-info/METADATA`. This is what catches the Shai-Hulud case: code that's still installed even though you rolled back the lockfile.

Turn this off to scan ~2-5x faster at the cost of those misses.

### `ecosystems`

Which lockfile/package formats to scan. Disabling here is mostly about avoiding spurious work — if you have no Go projects, drop `"go"`.

## `[feeds]`

### `osv` / `openssf` / `aikido`

Toggle each feed. We strongly recommend leaving all three on. See [feeds.md](feeds.md) for what each one covers and their licensing.

### `refresh_minutes`

How often the `watch` daemon re-polls feeds. Not used by one-shot `scan` (which refreshes every run unless `--skip-update`) or by `install-autostart` (which uses `[daemon].interval_minutes`).

### `max_age_hours`

If any enabled feed is older than this when the TUI launches, a background refresh kicks off. Default 24. Set higher if you're on a slow connection or pay for bandwidth.

## `[alerts.discord]`

### `webhook`

Paste a Discord webhook URL here to get hit alerts in a channel. The channel gets pinged with `@here` on CRITICAL severity only; HIGH and INFO are silent posts.

To create a webhook: Discord Server Settings → Integrations → Webhooks → New Webhook → copy URL.

## `[alerts.toast]`

### `enabled`

Native desktop toast notifications. Uses `winotify` on Windows (install with `pip install taintwatch[toast]`), `osascript` on macOS, `notify-send` on Linux. See [severity.md](severity.md) for the sound per severity level.

## `[alerts.report]`

### `dir`

Where to write the markdown report files. Empty means `<state_dir>/reports`. Each scan with new hits drops a `hits-YYYYMMDD-HHMMSS-<severity>.md` file there.

## `[daemon]`

### `interval_minutes`

How often the `watch` foreground daemon AND `install-autostart` scheduler entry run a scan. `install-autostart --interval N` overrides this for the scheduler entry.

## Editing the file

Either edit it in your normal editor (`taintwatch config path` prints the location) or open it from the TUI home screen with **c**.

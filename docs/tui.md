# The interactive TUI

Running `taintwatch` with no arguments launches a full-screen interactive UI built on [Textual](https://textual.textualize.io/). Same for `taintwatch ui`.

## Layout

```
┌─ ⌬ taintwatch v0.1.0   advisories: 225,251   feeds: 2h ago   roots: Portfolio ┐
└───────────────────────────────────────────────────────────────────────────────┘

  ╭─ menu ────────────────────────────────╮
  │ [s] Run scan now                      │
  │ [u] Update feeds                      │
  │ [h] View last scan's hits             │
  │ [f] Feed status                       │
  │ [r] Open report folder                │
  │ [c] Open config file                  │
  │ [q] Quit                              │
  ╰───────────────────────────────────────╯
```

The status bar shows:
- **advisories** — count of cached records in your local SQLite
- **feeds** — age of the *oldest* enabled feed. Green when <24h, amber 24–72h, red >72h. Reads "refreshing…" while a background refresh is in flight.
- **roots** — the scan roots configured in your `config.toml`.

## Screens

### Home
The menu. Arrow keys + enter, or press the highlighted single-letter shortcut.

### Scan
Runs feed-refresh + scan in a background thread. The screen is a live log; you can leave it and the worker keeps going. On completion the log tells you to press **h** to triage the new hits.

### Hits
Table of new findings. Cursor a row and press **enter** for the full advisory detail (severity, summary, references, repo + on-disk paths, copy-pastable remediation command). In the detail screen, **o** opens the first reference URL in your browser.

### Feeds
Status of every feed: last fetched timestamp, count of records, error message if the last pull failed. Press **u** to force-refresh.

## Keybindings

| Key | Anywhere | Home only | Hit detail |
|---|---|---|---|
| `q` / `esc` | Back / Quit | — | Close |
| `s` | — | Run scan | — |
| `u` | — | Update feeds | — |
| `h` | — | View hits | — |
| `f` | — | Feed status | — |
| `r` | — | Open report folder | — |
| `c` | — | Open config file | — |
| `o` | — | — | Open advisory URL |
| `↑` / `↓` / `enter` | Menu / table navigation |  | |
| `ctrl+c` | Force-quit |

## Auto-refresh

When you open the TUI, if any enabled feed is older than `[feeds] max_age_hours` (default 24), a background worker pulls fresh data without blocking you. The status bar reflects the state in real time.

## First-launch prompt

The first time you ever run the TUI, a welcome modal asks whether to install a scheduled background scan. Choose `y` (daily, recommended), `h` (hourly), or `n` (never ask again). The marker file at `<state_dir>/first-launch-seen` prevents the prompt from reappearing.

## Headless / piped mode

The bare `taintwatch` command does not launch the TUI when stdout is not a TTY — it falls back to showing help. For scripts and cron use the subcommands directly (`taintwatch scan`, `taintwatch feeds update`, etc.) which are TTY-agnostic.

## Why a TUI

The CLI subcommands handle the "I want a one-shot" case. The TUI handles the "I just want to see what's going on" case: hit triage with a real detail view, ambient feed-age visibility, and the welcome flow that gets a brand-new user from `pipx install` to a working scheduled scan in one keypress.

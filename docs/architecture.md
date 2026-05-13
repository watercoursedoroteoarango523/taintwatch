# Architecture

One Python package, one process per invocation, one SQLite file for state. No external services, no daemon framework, no cloud, no telemetry.

```
                    ┌──────────────────────┐
                    │  Config (TOML)       │
                    │  roots, channels,    │
                    │  excludes, schedule  │
                    └──────────┬───────────┘
                               │
   ┌───────────────────────────┼───────────────────────────┐
   │                           │                           │
┌──▼──────────┐         ┌──────▼──────────┐         ┌──────▼──────┐
│ Feed module │         │ Scanner module  │         │ Alert       │
│  (poller)   │         │                 │         │  module     │
├─────────────┤         ├─────────────────┤         ├─────────────┤
│ OSV bulk    │         │ Repo discover   │         │ Discord     │
│ OpenSSF git │ ───►    │ Lockfile parse  │ ───►    │ Toast (OS)  │
│ Aikido JSON │         │ Installed walk  │         │ Stdout      │
│             │         │ Diff vs last    │         │ Markdown    │
│ → SQLite    │         │  scan           │         │  report     │
└─────────────┘         └─────────────────┘         └─────────────┘
                               │
                       ┌───────▼───────┐
                       │ SQLite cache  │
                       │  advisories,  │
                       │  scan state,  │
                       │  alert log    │
                       └───────────────┘
```

## Subsystems

### Feed module (`taintwatch.feeds`)

Pluggable fetchers, one per source. Each subclasses `Fetcher` and exposes `update(conn, *, force=False) -> int` (count of upserted records). Three fetchers in v1: `osv.py`, `openssf.py`, `aikido.py`. All three normalize their native shapes into the same OSV-style `Advisory` dataclass and `state.upsert_advisory` writes them into the local DB.

`feeds.is_stale(conn, cfg)` checks the age of the oldest enabled feed against `cfg.feeds.max_age_hours` — used by the TUI to decide whether to kick off a background refresh on launch.

### Scanner module (`taintwatch.scanner`)

The matcher. One scan cycle does:

1. **Discover.** Walk every configured root. A directory is a repo if it has `.git/` or any known lockfile.
2. **Parse.** Run every applicable parser on the discovered lockfiles. Each parser returns `set[InstalledPkg(ecosystem, name, version, source, repo_path, lockfile_path)]`. Cached against `(repo, max-mtime-of-lockfiles)` so unchanged repos skip the reparse on the next run.
3. **Walk installed (deep mode).** Walk `node_modules/*/package.json` and `*/site-packages/*.dist-info/METADATA` to catch installed-but-not-in-lockfile cases (the Shai-Hulud scenario where you rolled back the lockfile but didn't `rm -rf node_modules`).
4. **Match.** For each `(ecosystem, name)`, look up the advisories; `version_match.is_affected(version, advisory)` decides hit-or-miss.
5. **Dedupe.** Hits are keyed by `(advisory_id, repo_path, version)`. The lockfile representative is preferred over installed when both exist for the same hit.
6. **Diff.** Compare against the previous run's hit set for "new this run" annotation.
7. **Dispatch.** Each alert channel that doesn't have a row in `alert_log` for this `(advisory, repo, channel)` triple gets notified. Channels that throw are tried again next run (no row, no record).

### Version matching (`taintwatch.version_match`)

Cross-ecosystem. PyPI uses `packaging.version.Version`; npm / crates.io / Go go through an in-house SemVer parser. The key load-bearing rule (and a regression test):

> **If an advisory has a non-empty `versions` list, that list is authoritative; range matching is skipped.** OSV malicious-package records routinely pair an explicit list with a stub `{introduced: "0"}` range as a metadata marker. Treating the stub as a real range false-positives every install.

### Alerts (`taintwatch.alerts`)

Four channels in v1: `stdout`, `report` (markdown file), `discord` (webhook), `toast` (OS native). Each is an `AlertChannel` subclass with `send(hits, severity)`. The severity is computed once per batch via `severity.classify(hits)` and passed to every channel that cares.

Dedupe is **per-channel** via `alert_log(advisory_id, repo_path, channel) PRIMARY KEY`. This means a Discord 5xx on run 1 will retry on run 2 even if the diff says "no new hits." See [severity.md](severity.md) for what the tiers do.

### Scheduler (`taintwatch.scheduler`)

Three implementations of `Scheduler.install(interval_minutes)`:
- **Windows** writes a Task Scheduler job via `schtasks /Create /SC MINUTE`.
- **macOS** writes `~/Library/LaunchAgents/dev.taintwatch.plist` with `StartInterval` and runs `launchctl load`.
- **Linux** writes `~/.config/systemd/user/taintwatch.{service,timer}` and `systemctl --user enable --now`.

All three register the same command: `taintwatch scan`. There is no long-lived service — scheduled execution is more robust on a dev laptop (sleep/resume, no orphans).

## State (`taintwatch.state`)

Single SQLite file at `<data_dir>/taintwatch/state.db`. Schema:

```sql
advisories(id PK, ecosystem, name, affected_json, summary, severity,
           source, references_json, first_seen, last_seen)
scan_runs(id PK, started_at, finished_at, repos_scanned, hits_count)
hits(scan_run_id FK, advisory_id FK, ecosystem, name, version,
     repo_path, lockfile_path, installed_path, source)
alert_log(advisory_id, repo_path, channel, sent_at) PRIMARY KEY (a,r,c)
feeds(name PK, last_etag, last_fetched, status)
lockfile_cache(repo_path, lockfile_path, mtime_ns, pkgs_json) PRIMARY KEY (r,l)
```

WAL mode, `synchronous=NORMAL`, foreign keys on. Schema version is tracked via `PRAGMA user_version` — there are no v0.x migrations because we're pre-1.0.

## Entry points

- `taintwatch` → `cli.app` (typer). Bare invocation launches the TUI; subcommands are one-shots.
- `taintwatchd` → `cli.watch_entry` (alias for `taintwatch watch`).
- The TUI in `tui.py` is a Textual `App` with screens for home, scan, hits + detail modal, and feeds. It shares the same `feeds.update_all`, `scanner.run_scan`, `alerts.dispatch_new_hits` code path as the CLI subcommands — no behavior duplication.

## Threading

The TUI runs all I/O-heavy work (`feeds.update_all`, `scanner.run_scan`) in `@work(thread=True)` workers so the UI stays responsive. Progress is pushed back to widgets via `app.call_from_thread`. The CLI subcommands are single-threaded.

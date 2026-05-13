# Changelog

All notable changes to taintwatch are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-12

### Added

- Initial release.
- Scanner: walks lockfiles (npm, yarn, pnpm, pip requirements, Pipfile.lock, Poetry, Cargo, Go modules) and (deep-scan mode) installed package directories (`node_modules/`, `*/site-packages/`).
- Feeds: OSV.dev bulk mirror (filtered to `MAL-*` records), OpenSSF `malicious-packages` git archive, Aikido Intel JSON. ~225k advisories cached locally.
- Local-only state in a single SQLite file. No cloud, no telemetry.
- Diff-aware: alerts only on *new* hits, per-channel dedupe via the `alert_log` table.
- Three-tier severity (CRITICAL / HIGH / INFO) maps to escalating toast sounds per OS; `@here` Discord pings on CRITICAL only.
- Interactive TUI built on Textual: home menu, live scan progress, hit triage with advisory drilldown, feed status. Launches by default when you run `taintwatch` with no arguments.
- Auto-refresh: stale feeds (>24h by default) refresh in the background on TUI launch.
- First-launch prompt: offers to enable per-OS scheduled autostart (Task Scheduler / launchd / systemd-user) on first run.
- Opt-in autostart subcommands: `install-autostart`, `uninstall-autostart`, `autostart-status`.
- Alert channels: stdout (rich table), markdown report file, Discord webhook, native desktop toast.
- One-liner installers (`install.sh`, `install.ps1`) and a PyPI Trusted Publishing release workflow.

[Unreleased]: https://github.com/braasdas/taintwatch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/braasdas/taintwatch/releases/tag/v0.1.0

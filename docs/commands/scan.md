# `taintwatch scan`

Run one scan cycle: refresh feeds (optional), discover repos, parse lockfiles, walk installed dirs (optional), match against the advisory DB, alert on new hits, exit.

## Synopsis

```sh
taintwatch scan [--root PATH]... [--deep|--no-deep] [--update-feeds|--skip-update] [--quiet]
```

## Options

| Flag | Default | Description |
|---|---|---|
| `--root PATH`, `-r PATH` | from config | Override `[scan] roots`. Repeatable. |
| `--deep` / `--no-deep` | from config (`true`) | Also walk `node_modules` and `*/site-packages/*.dist-info/METADATA`. |
| `--update-feeds` / `--skip-update` | `--update-feeds` | Refresh feeds before scanning. Skip to scan against the local cache only. |
| `--quiet`, `-q` | off | Suppress the brand banner; only print results. Use this in cron / CI. |

## Behavior

1. If `--update-feeds` (the default), pull every enabled feed and upsert into the local SQLite cache.
2. Walk every root, find repos by `.git/` or known lockfile.
3. For each repo, run every applicable parser. Cached by lockfile mtime.
4. In `--deep` mode, also walk `node_modules` / `site-packages`.
5. Match every `(ecosystem, name, version)` against the advisory DB.
6. Dedupe identical hits across nested installs.
7. Diff against the previous scan's hits. Newly-discovered hits go to every configured alert channel that hasn't already been notified for that `(advisory, repo, channel)`.
8. Exit 0.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Scan completed (regardless of whether hits were found) |
| 2 | No scan roots configured |

## Examples

One-shot scan with the configured roots, refresh feeds first:

```sh
taintwatch scan
```

Ad-hoc scan of a specific tree without touching the cache or the network:

```sh
taintwatch scan --root ~/work/project --skip-update --no-deep
```

For a cron job: silent unless something fires an alert:

```sh
taintwatch scan --quiet
```

## See also

- [commands/feeds.md](feeds.md) — manual feed refresh
- [commands/install-autostart.md](autostart.md) — register this command on the OS scheduler
- [configuration.md](../configuration.md) — `[scan]` config options
- [severity.md](../severity.md) — what the alert tiers mean

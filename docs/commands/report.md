# `taintwatch report`

View saved scan reports.

## Subcommands

| Command | Description |
|---|---|
| `taintwatch report show` | Print the contents of the N most recent report files. |

## `taintwatch report show`

### Synopsis

```sh
taintwatch report show [--last N] [-n N]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--last N`, `-n N` | 1 | How many recent reports to print. |

### Behavior

Reads the report directory (`<state_dir>/reports` by default, configurable via `[alerts.report] dir`) and prints the most recent `hits-*.md` files in descending timestamp order. Reports are written every time a scan finds new hits.

### Example

```sh
taintwatch report show
taintwatch report show -n 5    # last 5 reports
```

### Report filename format

`hits-YYYYMMDD-HHMMSS-<severity>.md`

The severity suffix mirrors the [tier](../severity.md) of that batch: `critical`, `high`, or `info`. Useful for filtering with shell globs: `ls $TAINTWATCH_REPORTS/*-critical.md`.

## See also

- [severity.md](../severity.md) — what the per-file severity means
- [configuration.md](../configuration.md) — `[alerts.report] dir`

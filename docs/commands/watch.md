# `taintwatch watch` / `taintwatchd`

Foreground daemon: loop forever, refreshing feeds and running a scan at the configured interval.

## Synopsis

```sh
taintwatch watch
taintwatchd            # alias
```

## Description

`watch` is the long-lived version of [`scan`](scan.md). It runs:

```
loop forever:
  feeds.update_all()
  run_scan()
  if new_hits: dispatch_new_hits()
  sleep [daemon].interval_minutes minutes
```

Use this when you want to leave taintwatch running in a terminal you can see. For unattended scheduled execution, prefer [`install-autostart`](autostart.md) — the OS scheduler is more robust against laptop sleep / resume.

## Options

None. Controlled entirely by config.

## Stop

Press `Ctrl+C`. The current scan cycle finishes before exit.

## Examples

```sh
taintwatch watch
```

Or, equivalently:

```sh
taintwatchd
```

## See also

- [commands/scan.md](scan.md) — one-shot variant
- [commands/install-autostart.md](autostart.md) — better for unattended use
- [configuration.md](../configuration.md) — `[daemon] interval_minutes`

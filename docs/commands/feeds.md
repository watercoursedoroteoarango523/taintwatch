# `taintwatch feeds`

Manage the local cache of malicious-package advisories.

## Subcommands

| Command | Description |
|---|---|
| `taintwatch feeds update` | Pull every enabled feed and upsert advisories into the SQLite cache. |
| `taintwatch feeds status` | Show last-fetched timestamps and status per feed. |

## `taintwatch feeds update`

### Synopsis

```sh
taintwatch feeds update [--force]
```

### Options

| Flag | Description |
|---|---|
| `--force` | Reserved for future ETag-aware refresh logic; currently a no-op. |

### Behavior

For each feed enabled in `[feeds]`:
1. Fetch the upstream payload.
2. Normalize records to OSV-shaped `Advisory` rows.
3. Upsert into the `advisories` table by `id`.

Prints per-feed status and the total cached count.

### Example

```
$ taintwatch feeds update
osv: ok (224440 new/updated)
openssf: ok (225082 new/updated)
aikido: ok (0 new/updated)
total advisories cached: 225251
```

## `taintwatch feeds status`

### Synopsis

```sh
taintwatch feeds status
```

### Output

A heavy-bordered table with one row per feed:

```
                    ⌬ feeds                    
┌─────────┬─────────────────────┬─────────────┐
│ name    │ last_fetched        │ status      │
├─────────┼─────────────────────┼─────────────┤
│ aikido  │ 2026-05-12 21:54:07 │ ok (0)      │
│ openssf │ 2026-05-12 21:54:06 │ ok (225082) │
│ osv     │ 2026-05-12 21:53:02 │ ok (224440) │
└─────────┴─────────────────────┴─────────────┘
advisories cached: 225251
```

## See also

- [feeds.md](../feeds.md) — the three feed sources, schemas, licensing
- [configuration.md](../configuration.md#feeds) — `[feeds]` options

# taintwatch docs

These docs cover what taintwatch does, how to install and configure it, every command it exposes, and how the matcher actually decides a package is compromised.

## Start here

- **[install.md](install.md)** — getting the binary onto every platform.
- **[tui.md](tui.md)** — the interactive UI (default mode of `taintwatch`).
- **[configuration.md](configuration.md)** — the `config.toml` reference.

## Reference

- **[feeds.md](feeds.md)** — the three feed sources, what they cover, licensing.
- **[severity.md](severity.md)** — what CRITICAL / HIGH / INFO mean and what sounds play.
- **[architecture.md](architecture.md)** — how the scanner, feed fetchers, and SQLite cache fit together.

## Commands

Every CLI command has its own page:

| Command | Doc |
|---|---|
| `taintwatch` / `taintwatch ui` | [commands/ui.md](commands/ui.md) |
| `taintwatch scan` | [commands/scan.md](commands/scan.md) |
| `taintwatch watch` (alias `taintwatchd`) | [commands/watch.md](commands/watch.md) |
| `taintwatch feeds update`, `taintwatch feeds status` | [commands/feeds.md](commands/feeds.md) |
| `taintwatch install-autostart`, `uninstall-autostart`, `autostart-status` | [commands/autostart.md](commands/autostart.md) |
| `taintwatch config init`, `taintwatch config path` | [commands/config.md](commands/config.md) |
| `taintwatch report show` | [commands/report.md](commands/report.md) |

# `taintwatch` / `taintwatch ui`

Launches the interactive TUI.

## Synopsis

```sh
taintwatch                # default action when no subcommand is given
taintwatch ui             # explicit alias
```

## Description

A bare `taintwatch` invocation launches a Textual-based full-screen UI. The TUI is the recommended way to use taintwatch interactively: it auto-refreshes stale feeds, surfaces feed age in the status bar, provides hit-triage with advisory drilldowns, and onboards new users with a one-keypress autostart prompt on first run.

## Options

This command takes no flags. To pass scan options non-interactively, use the [`scan`](scan.md) subcommand.

## Examples

```sh
taintwatch
```

Same as `taintwatch ui`.

## See also

- [tui.md](../tui.md) — full TUI walkthrough (screens, keybindings, auto-refresh)
- [commands/scan.md](scan.md) — non-interactive one-shot scan
- [commands/watch.md](watch.md) — foreground daemon (no TUI)

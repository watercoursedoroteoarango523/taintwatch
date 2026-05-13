# Install

taintwatch is a Python package. The recommended install path on every platform is **pipx**, which puts it in its own venv and gets the `taintwatch` and `taintwatchd` commands on your PATH.

## One-liner installers

These detect whether pipx and Python are available, install them if not, then install taintwatch.

**macOS / Linux**

```sh
curl -sSL https://raw.githubusercontent.com/braasdas/taintwatch/master/install.sh | sh
```

**Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/braasdas/taintwatch/master/install.ps1 | iex
```

## Manual install with pipx

If you already have Python 3.10+ and pipx:

```sh
pipx install taintwatch
```

## With pip (not recommended)

`pip install --user taintwatch` works but leaks taintwatch's dependencies into your user site-packages. pipx is strictly better.

## From source

```sh
git clone https://github.com/braasdas/taintwatch.git
cd taintwatch
pip install -e ".[dev,toast]"
```

The `toast` extra pulls in `winotify` on Windows (used for native toast notifications). On macOS and Linux toast goes through `osascript` and `notify-send` respectively — no extra deps needed.

## After install

```sh
taintwatch config init           # write a starter config
taintwatch                       # launches the TUI
```

The first time you launch the TUI it offers to enable a daily background scan via your OS scheduler. You can decline and run it manually instead.

## Upgrade

```sh
pipx upgrade taintwatch          # or: pipx upgrade-all
```

## Uninstall

```sh
taintwatch uninstall-autostart   # remove the scheduler entry first, if you set it
pipx uninstall taintwatch
```

State, config, and reports live under standard OS data directories and are NOT removed when you uninstall the package. Delete them manually if you want a complete cleanup:

- **Windows** `%LOCALAPPDATA%\taintwatch` and `%APPDATA%\taintwatch`
- **macOS** `~/Library/Application Support/taintwatch` and `~/Library/Application Support/taintwatch`
- **Linux** `~/.local/share/taintwatch` and `~/.config/taintwatch`

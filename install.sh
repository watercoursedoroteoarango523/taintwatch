#!/bin/sh
# taintwatch one-liner installer — macOS and Linux.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/braasdas/taintwatch/master/install.sh | sh
#
# What it does:
#   1. Ensures pipx is installed (via brew / apt / dnf / pacman, falling back
#      to `python3 -m pip install --user pipx`).
#   2. Runs `pipx install taintwatch` (or upgrades if already installed).
#   3. Prints next-step commands.
#
# What it does NOT do:
#   - Configure autostart. You have to opt in with `taintwatch install-autostart`.
#   - Read or transmit anything from your machine.

set -eu

have() { command -v "$1" >/dev/null 2>&1; }

note() { printf '\033[36m[taintwatch]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[taintwatch]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[taintwatch]\033[0m %s\n' "$*" >&2; exit 1; }

ensure_python() {
  if have python3; then return; fi
  if have python; then return; fi
  fail "Python 3.10+ is required. Install it from https://www.python.org/downloads/ and re-run."
}

ensure_pipx() {
  if have pipx; then return; fi
  note "pipx not found — installing it"
  if have brew; then
    brew install pipx
  elif have apt-get; then
    sudo apt-get update >/dev/null
    sudo apt-get install -y pipx
  elif have dnf; then
    sudo dnf install -y pipx
  elif have pacman; then
    sudo pacman -S --noconfirm python-pipx
  else
    PY="$(command -v python3 || command -v python)"
    "$PY" -m pip install --user pipx
    "$PY" -m pipx ensurepath
  fi
  hash -r 2>/dev/null || true
  if ! have pipx; then
    warn "pipx installed but not on PATH for THIS shell session."
    warn "Open a new terminal and re-run, or add ~/.local/bin to your PATH."
    fail "Aborting."
  fi
}

main() {
  ensure_python
  ensure_pipx
  pipx ensurepath >/dev/null 2>&1 || true
  if pipx list 2>/dev/null | grep -q '^   package taintwatch '; then
    note "taintwatch is already installed — upgrading"
    pipx upgrade taintwatch
  else
    note "Installing taintwatch"
    pipx install taintwatch
  fi
  note "Installed. Next steps:"
  printf "  taintwatch config init\n"
  printf "  taintwatch feeds update\n"
  printf "  taintwatch scan\n"
  printf "\nOptional: enable hourly background checks with:\n"
  printf "  taintwatch install-autostart --interval 60\n"
}

main "$@"

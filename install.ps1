# taintwatch one-liner installer — Windows PowerShell.
#
# Usage (in a fresh PowerShell window):
#   irm https://raw.githubusercontent.com/braasdas/taintwatch/master/install.ps1 | iex
#
# What it does:
#   1. Ensures Python 3.10+ is on PATH (suggests winget / Scoop if missing).
#   2. Ensures pipx is installed.
#   3. Runs `pipx install taintwatch` (or upgrades if already installed).
#   4. Prints next-step commands.
#
# What it does NOT do:
#   - Configure autostart. You have to opt in with `taintwatch install-autostart`.
#   - Read or transmit anything from your machine.

$ErrorActionPreference = 'Stop'

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Note($msg) { Write-Host "[taintwatch] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[taintwatch] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[taintwatch] $msg" -ForegroundColor Red; exit 1 }

function Ensure-Python {
  if (Have python) { return }
  if (Have py)     { return }
  Warn "Python 3.10+ is not on PATH."
  if (Have winget) {
    Note "Installing Python 3.12 via winget"
    winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
  } elseif (Have scoop) {
    Note "Installing Python via Scoop"
    scoop install python
  } else {
    Fail "Install Python 3.10+ from https://www.python.org/downloads/windows/ and re-run."
  }
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
  if (-not (Have python)) { Fail "Python install succeeded but it's not on PATH in this session. Open a new PowerShell window and re-run." }
}

function Ensure-Pipx {
  if (Have pipx) { return }
  Note "Installing pipx"
  python -m pip install --user pipx | Out-Null
  python -m pipx ensurepath | Out-Null
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
  if (-not (Have pipx)) { Fail "pipx installed but not on PATH in this session. Open a new PowerShell window and re-run." }
}

Ensure-Python
Ensure-Pipx

$existing = & pipx list 2>$null | Select-String -SimpleMatch "package taintwatch "
if ($existing) {
  Note "taintwatch is already installed — upgrading"
  pipx upgrade taintwatch
} else {
  Note "Installing taintwatch"
  pipx install taintwatch
}

Note "Installed. Next steps:"
Write-Host "  taintwatch config init"
Write-Host "  taintwatch feeds update"
Write-Host "  taintwatch scan"
Write-Host ""
Write-Host "Optional: enable hourly background checks with:"
Write-Host "  taintwatch install-autostart --interval 60"

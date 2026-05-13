"""Visual identity for the CLI — derived from the taintwatch logo.

The logo is a six-petal cream spiral with one petal rendered in a poison-lime
gradient and pierced by a black entomology pin. The CLI palette mirrors that:

- Cream petals      -> body text on a dark terminal
- Poison lime       -> brand accent, "clean" / "found-it" signals
- Pin (black/dim)   -> structural borders, separators
- Red (escape)      -> only for CRITICAL, where it has to be red

The pin glyph (◉⟶) is the find marker: the moment the scanner sticks a hit.

Banner is intentionally small — taintwatch may run on a cron, and the user
doesn't need a six-line ASCII spiral every minute. One line, one glyph.
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import __version__


# ── Palette ──────────────────────────────────────────────────────────────────
LIME = "#9CFF4B"          # poison-green petal
LIME_DIM = "#5BB52D"      # lower-saturation green for less-important lime
CREAM = "#EEEAD9"         # cream petals — body text
PIN = "#222222"           # black pin — borders (terminals will treat as bg-adjacent)
PIN_SOFT = "grey50"       # rich-named, falls back well
DANGER = "#FF4D4D"        # CRITICAL only — breaks the cream/lime scheme on purpose
WARN = "#FFB85F"          # HIGH — warm amber, complement to lime

# Glyphs from the logo's vocabulary.
SPIRAL = "⌬"              # six-petal stand-in
PIN_GLYPH = "◉"           # the dot at the end of the entomology pin
PIN_ARROW = "◉⟶"          # the pin sticking the petal
TAINTED = "🌶"            # one tainted petal (used sparingly — emoji are optional)

# Rich styles you can pass as the `style=` arg or wrap in [brackets].
STYLE_BRAND = f"bold {LIME}"
STYLE_CLEAN = f"bold {LIME}"
STYLE_BODY = CREAM
STYLE_DIM = PIN_SOFT
STYLE_CRITICAL = f"bold {DANGER}"
STYLE_HIGH = f"bold {WARN}"
STYLE_INFO = f"bold {LIME_DIM}"


def banner_line() -> Text:
    """One-line banner: spiral · taintwatch · version. Used at the head of scan/watch."""
    t = Text()
    t.append(f"{SPIRAL} ", style=STYLE_BRAND)
    t.append("taintwatch", style=f"bold {CREAM}")
    t.append(f"  v{__version__}", style=PIN_SOFT)
    return t


def banner(console: Console | None = None) -> None:
    """Render the banner unless we're piped to something that probably doesn't want it."""
    console = console or Console()
    if not _should_show_banner(console):
        return
    console.print(banner_line())


def panel_title() -> str:
    """Use for rich.Panel(title=...) so panels feel like petals."""
    return f"[{STYLE_BRAND}]{SPIRAL}[/] [bold {CREAM}]taintwatch[/]"


def _should_show_banner(console: Console) -> bool:
    if not console.is_terminal:
        return False
    if not sys.stdout.isatty():
        return False
    return True


# Used by stdout/report channels for severity-tinted headers.
SEVERITY_STYLE = {
    "critical": (STYLE_CRITICAL, f"{PIN_ARROW} CRITICAL — compromised code installed on disk"),
    "high": (STYLE_HIGH, f"{PIN_ARROW} HIGH — compromised package in lockfile"),
    "info": (STYLE_INFO, f"{SPIRAL} taintwatch"),
}

"""Interactive TUI for taintwatch, built on Textual.

Launched by running `taintwatch` with no arguments (or `taintwatch ui`).
The one-shot subcommands (scan, watch, feeds update, etc.) still work
unchanged for cron / scripting.

Screens:
  Home   — banner, status, menu
  Scan   — live scrolling log while a scan worker runs in a thread
  Hits   — DataTable of current findings; enter opens a detail modal
  Feeds  — DataTable of feed status

The brand palette lives in `branding.py` and is mirrored into a CSS
stylesheet below so Textual can render it.
"""
from __future__ import annotations

import sqlite3
import time
import webbrowser
from pathlib import Path
from typing import Iterable

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    DataTable,
    Footer,
    Label,
    ListItem,
    ListView,
    Markdown,
    RichLog,
    Static,
)

from . import __version__, branding
from . import config as cfgmod
from . import feeds as feeds_mod
from . import paths
from .alerts import dispatch_new_hits
from .alerts.severity import Severity, classify
from .models import Hit
from .scanner import run_scan
from .state import count_advisories, get_advisory, get_feeds_status, open_db


# ── CSS ──────────────────────────────────────────────────────────────────────
# Textual CSS supports the rich color names + hex. We define a few semantic
# classes that mirror the brand palette so widgets stay consistent.

CSS = f"""
Screen {{
    background: black;
    color: {branding.CREAM};
}}

.banner {{
    color: {branding.LIME};
    text-style: bold;
    padding: 1 2;
}}

.brand {{
    color: {branding.LIME};
    text-style: bold;
}}

.dim {{
    color: $accent-darken-2;
}}

.cream {{
    color: {branding.CREAM};
}}

.critical {{
    color: {branding.DANGER};
    text-style: bold;
}}

.high {{
    color: {branding.WARN};
    text-style: bold;
}}

#status-bar {{
    height: 3;
    border: heavy {branding.LIME};
    padding: 0 1;
}}

#menu {{
    height: auto;
    border: round {branding.LIME};
    padding: 1 2;
    margin: 1 2;
}}

#menu > ListItem {{
    padding: 0 1;
}}

#menu > ListItem.--highlight {{
    background: {branding.LIME} 30%;
    color: {branding.LIME};
    text-style: bold;
}}

#scan-log {{
    border: heavy {branding.LIME};
    padding: 0 1;
    margin: 1 2;
    height: 1fr;
}}

DataTable {{
    border: heavy {branding.LIME};
    margin: 1 2;
}}

DataTable > .datatable--header {{
    color: {branding.LIME};
    text-style: bold;
}}

DataTable > .datatable--cursor {{
    background: {branding.LIME} 20%;
}}

#detail {{
    border: round {branding.LIME};
    padding: 1 2;
    margin: 1 4;
}}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("scan", "Run scan now", "s"),
    ("update", "Update feeds", "u"),
    ("hits", "View last scan's hits", "h"),
    ("feeds", "Feed status", "f"),
    ("reports", "Open report folder", "r"),
    ("config", "Open config file", "c"),
    ("quit", "Quit", "q"),
]


def _status_text(cfg: cfgmod.Config, n_advisories: int) -> Text:
    t = Text()
    t.append(f"{branding.SPIRAL} ", style=branding.STYLE_BRAND)
    t.append("taintwatch ", style=f"bold {branding.CREAM}")
    t.append(f"v{__version__}", style=branding.PIN_SOFT)
    t.append("   ")
    t.append("advisories cached: ", style=branding.PIN_SOFT)
    t.append(f"{n_advisories:,}", style=branding.STYLE_BRAND)
    t.append("   ")
    t.append("roots: ", style=branding.PIN_SOFT)
    t.append(
        ", ".join(p.name for p in cfg.scan.roots) if cfg.scan.roots else "<none — run config init>",
        style=branding.CREAM,
    )
    return t


# ── Screens ──────────────────────────────────────────────────────────────────


class HomeScreen(Screen):
    BINDINGS = [
        Binding("s", "select('scan')", "Scan"),
        Binding("u", "select('update')", "Feeds"),
        Binding("h", "select('hits')", "Hits"),
        Binding("f", "select('feeds')", "Status"),
        Binding("r", "select('reports')", "Reports"),
        Binding("c", "select('config')", "Config"),
        Binding("q", "select('quit')", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        cfg = self.app.cfg
        with open_db() as conn:
            n = count_advisories(conn)
        yield Static(_status_text(cfg, n), id="status-bar")
        items = []
        for key, label, hot in MENU_ITEMS:
            text = Text()
            text.append(f"[{hot}] ", style=branding.STYLE_BRAND)
            text.append(label, style=branding.CREAM)
            li = ListItem(Label(text))
            li.menu_key = key  # type: ignore[attr-defined]
            items.append(li)
        yield ListView(*items, id="menu")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ListView).focus()

    def action_select(self, key: str) -> None:
        self._go(key)

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        key = getattr(event.item, "menu_key", None)
        if key:
            self._go(key)

    def _go(self, key: str) -> None:
        if key == "scan":
            self.app.push_screen(ScanScreen())
        elif key == "update":
            self.app.push_screen(ScanScreen(feeds_only=True))
        elif key == "hits":
            self.app.push_screen(HitsScreen())
        elif key == "feeds":
            self.app.push_screen(FeedsScreen())
        elif key == "reports":
            self._open_reports()
        elif key == "config":
            self._open_config()
        elif key == "quit":
            self.app.exit()

    def _open_reports(self) -> None:
        rd = self.app.cfg.alerts.report.dir or paths.default_report_dir()
        rd.mkdir(parents=True, exist_ok=True)
        webbrowser.open(rd.as_uri())

    def _open_config(self) -> None:
        cp = paths.config_path()
        if cp.exists():
            webbrowser.open(cp.as_uri())


class ScanScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("h", "show_hits", "View hits"),
    ]

    def __init__(self, feeds_only: bool = False):
        super().__init__()
        self.feeds_only = feeds_only
        self._new_hits: list[Hit] = []
        self._all_hits: list[Hit] = []
        self._new_keys: set[tuple[str, str, str]] = set()

    def compose(self) -> ComposeResult:
        title = f"{branding.SPIRAL} updating feeds" if self.feeds_only else f"{branding.SPIRAL} scanning"
        yield Static(Text(title, style=branding.STYLE_BRAND), classes="banner")
        yield RichLog(id="scan-log", wrap=True, markup=True, highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write(f"[bold {branding.LIME}]{branding.SPIRAL} starting…[/]")
        if self.feeds_only:
            self._run_feeds_only()
        else:
            self._run_scan()

    @work(thread=True, exclusive=True)
    def _run_feeds_only(self) -> None:
        log = self.query_one(RichLog)
        with open_db() as conn:
            self.app.call_from_thread(
                log.write, f"[{branding.PIN_SOFT}]pulling OSV + OpenSSF + Aikido…[/]"
            )
            results = feeds_mod.update_all(conn, self.app.cfg)
            for k, v in results.items():
                self.app.call_from_thread(
                    log.write,
                    f"  [bold {branding.LIME_DIM}]{k}[/]: [{branding.CREAM}]{v}[/]",
                )
            n = count_advisories(conn)
            self.app.call_from_thread(
                log.write,
                f"\n[bold {branding.LIME}]{branding.SPIRAL} done.[/] "
                f"[{branding.PIN_SOFT}]advisories cached: {n:,}[/]",
            )

    @work(thread=True, exclusive=True)
    def _run_scan(self) -> None:
        log = self.query_one(RichLog)
        cfg = self.app.cfg

        if not cfg.scan.roots:
            self.app.call_from_thread(
                log.write,
                f"[{branding.DANGER}]No scan roots configured.[/] "
                f"Edit your config file and re-run.",
            )
            return

        with open_db() as conn:
            self.app.call_from_thread(
                log.write,
                f"[{branding.PIN_SOFT}]{branding.SPIRAL} refreshing feeds…[/]",
            )
            results = feeds_mod.update_all(conn, cfg)
            for k, v in results.items():
                self.app.call_from_thread(
                    log.write,
                    f"  [bold {branding.LIME_DIM}]{k}[/]: [{branding.CREAM}]{v}[/]",
                )
            n = count_advisories(conn)
            self.app.call_from_thread(
                log.write,
                f"  [{branding.PIN_SOFT}]advisories cached:[/] "
                f"[bold {branding.LIME}]{n:,}[/]\n",
            )

            self.app.call_from_thread(
                log.write,
                f"[{branding.PIN_SOFT}]{branding.SPIRAL} scanning roots: "
                f"{', '.join(p.as_posix() for p in cfg.scan.roots)}[/]",
            )
            t0 = time.time()
            run_id, all_hits, new_keys = run_scan(conn, cfg)
            dt = time.time() - t0
            new_hits = [
                h for h in all_hits
                if (h.advisory_id, str(h.pkg.repo_path), h.pkg.version) in new_keys
            ]

            if not new_hits:
                self.app.call_from_thread(
                    log.write,
                    f"\n[bold {branding.LIME}]{branding.SPIRAL} clean[/] "
                    f"[{branding.PIN_SOFT}]scan #{run_id} · {dt:.1f}s · "
                    f"{len(all_hits)} known matched · 0 new[/]",
                )
                return

            self.app.call_from_thread(
                log.write,
                f"\n[bold {branding.DANGER}]{branding.PIN_ARROW} "
                f"{len(new_hits)} new hit(s)[/] "
                f"[{branding.PIN_SOFT}]scan #{run_id} · {dt:.1f}s[/]",
            )
            sent = dispatch_new_hits(conn, cfg, all_hits, new_keys)
            for ch, sent_n in sent.items():
                tag = (
                    f"[{branding.DANGER}]error[/]"
                    if sent_n == -1
                    else f"[{branding.CREAM}]{sent_n} sent[/]"
                )
                self.app.call_from_thread(
                    log.write,
                    f"  [{branding.LIME_DIM}]{ch}[/]: {tag}",
                )

            self._new_hits = new_hits
            self._all_hits = all_hits
            self._new_keys = new_keys
            self.app.call_from_thread(
                log.write,
                f"\n[{branding.STYLE_BRAND}]press h to triage the hits[/]",
            )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_show_hits(self) -> None:
        if not self._new_hits:
            return
        self.app.push_screen(HitsScreen(hits=self._new_hits))


class HitsScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("enter", "details", "Details", show=False),
    ]

    def __init__(self, hits: list[Hit] | None = None):
        super().__init__()
        self._hits = hits or []

    def compose(self) -> ComposeResult:
        sev = classify(self._hits) if self._hits else Severity.INFO
        style, label = branding.SEVERITY_STYLE[sev.value]
        yield Static(Text(label, style=style), classes="banner")
        if not self._hits:
            yield Static(
                Text(
                    "No current hits. Run a scan from the home menu first.",
                    style=branding.CREAM,
                ),
                classes="dim",
            )
        else:
            table = DataTable(zebra_stripes=True, cursor_type="row")
            table.add_columns("eco", "package", "version", "advisory", "repo", "source")
            for h in self._hits:
                source_text = (
                    Text(f"{branding.PIN_GLYPH} installed", style=branding.STYLE_CRITICAL)
                    if h.pkg.source == "installed"
                    else Text("lockfile", style=branding.WARN)
                )
                table.add_row(
                    Text(h.pkg.ecosystem, style=branding.PIN_SOFT),
                    Text(h.pkg.name, style=branding.CREAM),
                    Text(h.pkg.version, style=branding.CREAM),
                    Text(h.advisory_id, style=branding.LIME_DIM),
                    Text(h.pkg.repo_path.name, style=branding.CREAM),
                    source_text,
                    key=str(id(h)),
                )
                table._hit_lookup = getattr(table, "_hit_lookup", {})  # type: ignore[attr-defined]
                table._hit_lookup[str(id(h))] = h  # type: ignore[attr-defined]
            yield table
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_details(self) -> None:
        if not self._hits:
            return
        try:
            table = self.query_one(DataTable)
        except Exception:
            return
        row_key = table.cursor_row
        # Walk through the hits list using the highlighted row index.
        if 0 <= row_key < len(self._hits):
            self.app.push_screen(HitDetailScreen(self._hits[row_key]))


class HitDetailScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("o", "open_reference", "Open advisory URL"),
    ]

    def __init__(self, hit: Hit):
        super().__init__()
        self._hit = hit

    def compose(self) -> ComposeResult:
        h = self._hit
        with open_db() as conn:
            adv = get_advisory(conn, h.advisory_id) or h.advisory
        loc = (
            h.pkg.installed_path
            if h.pkg.installed_path
            else (h.pkg.lockfile_path or h.pkg.repo_path)
        )
        md = f"""# `{h.pkg.name}@{h.pkg.version}` &nbsp;·&nbsp; *{h.pkg.ecosystem}*

**Advisory:** `{adv.id}` &nbsp;·&nbsp; source: {adv.source}
**Severity:** {adv.severity or "—"}
**Repo:** `{h.pkg.repo_path}`
**Where:** `{loc}` &nbsp;·&nbsp; **{h.pkg.source}**

---

{adv.summary or "_no summary in the feed_"}

---

### References

{chr(10).join('- ' + r for r in adv.references if r) or '_none_'}

### What to do

```
cd "{h.pkg.repo_path}"
{_remediation_command(h)}
```

(press **o** to open the first reference link in a browser)
"""
        yield Container(Markdown(md), id="detail")
        yield Footer()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def action_open_reference(self) -> None:
        adv = self._hit.advisory
        for r in adv.references:
            if r:
                webbrowser.open(r)
                return


def _remediation_command(h: Hit) -> str:
    if h.pkg.ecosystem == "npm":
        return (
            "rm -rf node_modules\n"
            f"npm uninstall {h.pkg.name}    # then pin a known-safe version\n"
            "npm install"
        )
    if h.pkg.ecosystem == "PyPI":
        return f"pip uninstall {h.pkg.name}   # then recreate venv from pinned-safe versions"
    if h.pkg.ecosystem == "crates.io":
        return f"cargo update -p {h.pkg.name}   # then pin a known-safe version"
    if h.pkg.ecosystem == "Go":
        return f"go get {h.pkg.name}@<safe-version>"
    return "# Remove the package and reinstall a vetted release."


class FeedsScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("u", "update", "Update now"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            Text(f"{branding.SPIRAL} feed status", style=branding.STYLE_BRAND),
            classes="banner",
        )
        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("feed", "last_fetched", "status")
        with open_db() as conn:
            rows = get_feeds_status(conn)
            for r in rows:
                ts = (
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["last_fetched"]))
                    if r["last_fetched"]
                    else "—"
                )
                table.add_row(
                    Text(r["name"], style=branding.LIME_DIM),
                    Text(ts, style=branding.CREAM),
                    Text(r["status"] or "—", style=branding.CREAM),
                )
            n = count_advisories(conn)
        yield table
        yield Static(
            Text(f"advisories cached: {n:,}   ·   press u to refresh", style=branding.PIN_SOFT),
            classes="dim",
        )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_update(self) -> None:
        self.app.push_screen(ScanScreen(feeds_only=True))


# ── App ──────────────────────────────────────────────────────────────────────


class TaintwatchApp(App):
    CSS = CSS
    TITLE = "taintwatch"
    SUB_TITLE = f"v{__version__}"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.cfg = cfgmod.load()

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


def run() -> None:
    TaintwatchApp().run()

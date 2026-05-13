from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import config as cfgmod
from . import feeds, paths
from .alerts import dispatch_new_hits
from .scanner import run_scan
from .scheduler import get as get_scheduler
from .state import (
    count_advisories,
    get_feeds_status,
    open_db,
)

app = typer.Typer(
    name="taintwatch",
    help="Scan your codebases for known-compromised package versions.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Config file management.")
feeds_app = typer.Typer(help="Feed management.")
report_app = typer.Typer(help="Reports.")
app.add_typer(config_app, name="config")
app.add_typer(feeds_app, name="feeds")
app.add_typer(report_app, name="report")

console = Console()


def _load() -> cfgmod.Config:
    cfg = cfgmod.load()
    if cfg.path and not cfg.path.exists():
        console.print(
            f"[yellow]No config at {cfg.path}. Run [bold]taintwatch config init[/bold] first.[/yellow]"
        )
    return cfg


@app.command()
def scan(
    root: list[Path] = typer.Option(None, "--root", "-r", help="Override config roots (repeatable)."),
    deep: Optional[bool] = typer.Option(None, "--deep/--no-deep", help="Also walk node_modules / site-packages."),
    update_feeds: bool = typer.Option(True, "--update-feeds/--skip-update", help="Refresh feeds before scanning."),
) -> None:
    """Run one scan cycle: optionally refresh feeds, then scan all roots, then alert on new hits."""
    cfg = _load()
    if root:
        cfg.scan.roots = [Path(p).expanduser().resolve() for p in root]
    if deep is not None:
        cfg.scan.deep_scan = deep

    if not cfg.scan.roots:
        console.print("[red]No scan roots configured.[/red] Run `taintwatch config init`.")
        raise typer.Exit(2)

    with open_db() as conn:
        if update_feeds:
            console.print("[bold]Updating feeds…[/bold]")
            results = feeds.update_all(conn, cfg)
            for k, v in results.items():
                console.print(f"  [cyan]{k}[/cyan]: {v}")
            console.print(f"  total advisories cached: [bold]{count_advisories(conn)}[/bold]")

        console.print(f"[bold]Scanning {len(cfg.scan.roots)} root(s)…[/bold] deep={cfg.scan.deep_scan}")
        t0 = time.time()
        run_id, all_hits, new_keys = run_scan(conn, cfg)
        dt = time.time() - t0
        new_hits = [h for h in all_hits if (h.advisory_id, str(h.pkg.repo_path), h.pkg.version) in new_keys]

        console.print(
            f"[green]Scan #{run_id} done in {dt:.1f}s — {len(all_hits)} total hit(s), [bold]{len(new_hits)} new[/bold].[/green]"
        )

        if not new_hits:
            console.print("[green]No new compromised packages found.[/green]")
            return

        sent = dispatch_new_hits(conn, cfg, all_hits, new_keys)
        for ch, n in sent.items():
            if n == -1:
                console.print(f"  alert channel [red]{ch}[/red]: error")
            else:
                console.print(f"  alert channel [cyan]{ch}[/cyan]: {n} sent")


@app.command()
def watch() -> None:
    """Foreground daemon: loop, refresh feeds, scan, sleep, repeat."""
    cfg = _load()
    if not cfg.scan.roots:
        console.print("[red]No scan roots configured.[/red]")
        raise typer.Exit(2)
    interval = max(60, cfg.daemon.interval_minutes * 60)
    console.print(f"[bold]taintwatch watch[/bold] — every {cfg.daemon.interval_minutes}m. Ctrl-C to stop.")
    try:
        while True:
            with open_db() as conn:
                feeds.update_all(conn, cfg)
                run_id, all_hits, new_keys = run_scan(conn, cfg)
                new_hits = [
                    h for h in all_hits
                    if (h.advisory_id, str(h.pkg.repo_path), h.pkg.version) in new_keys
                ]
                console.print(
                    f"[dim]{time.strftime('%H:%M:%S')}[/dim] scan #{run_id}: "
                    f"{len(all_hits)} total, {len(new_hits)} new"
                )
                if new_hits:
                    dispatch_new_hits(conn, cfg, all_hits, new_keys)
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("[yellow]watch stopped.[/yellow]")


def watch_entry() -> None:
    """Console-script entry for `taintwatchd`."""
    sys.argv.insert(1, "watch")
    app()


@config_app.command("init")
def config_init(
    root: Optional[Path] = typer.Option(None, "--root", help="Default scan root to seed."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config."),
) -> None:
    """Write a default config.toml."""
    path = paths.config_path()
    if path.exists() and not force:
        console.print(f"[yellow]{path} already exists. Use --force to overwrite.[/yellow]")
        raise typer.Exit(1)
    cfgmod.write_default(path, root.expanduser().resolve() if root else None)
    console.print(f"[green]wrote[/green] {path}")


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the resolved config path."""
    console.print(str(paths.config_path()))


@feeds_app.command("update")
def feeds_update(force: bool = typer.Option(False, "--force")) -> None:
    """Refresh all enabled feeds."""
    cfg = _load()
    with open_db() as conn:
        results = feeds.update_all(conn, cfg, force=force)
        for k, v in results.items():
            console.print(f"[cyan]{k}[/cyan]: {v}")
        console.print(f"total advisories cached: [bold]{count_advisories(conn)}[/bold]")


@feeds_app.command("status")
def feeds_status() -> None:
    """Show last-fetched timestamps and status per feed."""
    with open_db() as conn:
        rows = get_feeds_status(conn)
        table = Table(title="feeds")
        table.add_column("name")
        table.add_column("last_fetched")
        table.add_column("status")
        for r in rows:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["last_fetched"])) if r["last_fetched"] else "—"
            table.add_row(r["name"], ts, r["status"] or "—")
        console.print(table)
        console.print(f"total advisories cached: [bold]{count_advisories(conn)}[/bold]")


@app.command("install-autostart")
def install_autostart(
    interval: int = typer.Option(60, "--interval", help="Minutes between runs."),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """OPT-IN: register a per-OS scheduler entry that runs `taintwatch scan` every N minutes."""
    sch = get_scheduler()
    out = sch.install(interval, dry_run=dry_run)
    console.print(out)


@app.command("uninstall-autostart")
def uninstall_autostart() -> None:
    """Remove the per-OS scheduler entry."""
    sch = get_scheduler()
    out = sch.uninstall()
    console.print(out)


@app.command("autostart-status")
def autostart_status() -> None:
    """Show whether the per-OS scheduler entry is installed."""
    sch = get_scheduler()
    console.print(sch.status())


@report_app.command("show")
def report_show(last: int = typer.Option(1, "--last", "-n", help="Show the N most recent reports.")) -> None:
    """Print the contents of the most recent report file(s)."""
    cfg = _load()
    rd = cfg.alerts.report.dir or paths.default_report_dir()
    if not rd.exists():
        console.print(f"[yellow]No reports directory at {rd}.[/yellow]")
        raise typer.Exit(0)
    files = sorted(rd.glob("hits-*.md"), reverse=True)[: max(1, last)]
    if not files:
        console.print(f"[green]No report files in {rd}.[/green]")
        return
    for f in files:
        console.print(f"\n[bold cyan]── {f.name} ──[/bold cyan]\n")
        console.print(f.read_text(encoding="utf-8"))


if __name__ == "__main__":
    app()

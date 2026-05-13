from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ..models import Hit
from .base import AlertChannel
from .severity import Severity


_TITLE_STYLE = {
    Severity.CRITICAL: ("bold red", "CRITICAL — compromised code installed on disk"),
    Severity.HIGH: ("bold yellow", "HIGH — compromised package in lockfile"),
    Severity.INFO: ("bold cyan", "INFO"),
}


class StdoutChannel(AlertChannel):
    name = "stdout"

    def __init__(self) -> None:
        self.console = Console()

    def send(self, hits: list[Hit], severity: Severity = Severity.HIGH) -> None:
        if not hits:
            return
        style, label = _TITLE_STYLE[severity]
        table = Table(title=f"[{style}]taintwatch — {label}[/{style}]")
        table.add_column("eco")
        table.add_column("package")
        table.add_column("version")
        table.add_column("advisory")
        table.add_column("repo")
        table.add_column("source", style="red")
        for h in hits:
            source_cell = (
                "[bold red]installed[/bold red]"
                if h.pkg.source == "installed"
                else "lockfile"
            )
            table.add_row(
                h.pkg.ecosystem,
                h.pkg.name,
                h.pkg.version,
                h.advisory_id,
                h.pkg.repo_path.name,
                source_cell,
            )
        self.console.print(table)

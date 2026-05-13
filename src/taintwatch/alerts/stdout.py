from __future__ import annotations

from rich import box
from rich.console import Console
from rich.table import Table

from .. import branding
from ..models import Hit
from .base import AlertChannel
from .severity import Severity


class StdoutChannel(AlertChannel):
    name = "stdout"

    def __init__(self) -> None:
        self.console = Console()

    def send(self, hits: list[Hit], severity: Severity = Severity.HIGH) -> None:
        if not hits:
            return
        style, label = branding.SEVERITY_STYLE[severity.value]
        table = Table(
            title=f"[{style}]{label}[/]",
            box=box.HEAVY,
            border_style=branding.PIN_SOFT,
            header_style=f"bold {branding.LIME}",
            title_style=style,
        )
        table.add_column("eco", style=branding.PIN_SOFT)
        table.add_column("package", style=branding.CREAM, no_wrap=True)
        table.add_column("version", style=branding.CREAM)
        table.add_column("advisory", style=branding.LIME_DIM)
        table.add_column("repo", style=branding.CREAM)
        table.add_column("source")
        for h in hits:
            if h.pkg.source == "installed":
                source_cell = f"[bold {branding.DANGER}]{branding.PIN_GLYPH} installed[/]"
            else:
                source_cell = f"[{branding.WARN}]lockfile[/]"
            table.add_row(
                h.pkg.ecosystem,
                h.pkg.name,
                h.pkg.version,
                h.advisory_id,
                h.pkg.repo_path.name,
                source_cell,
            )
        self.console.print(table)

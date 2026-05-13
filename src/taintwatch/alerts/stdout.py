from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ..models import Hit
from .base import AlertChannel


class StdoutChannel(AlertChannel):
    name = "stdout"

    def __init__(self) -> None:
        self.console = Console()

    def send(self, hits: list[Hit]) -> None:
        if not hits:
            return
        table = Table(title="taintwatch — new hits this run")
        table.add_column("eco")
        table.add_column("package")
        table.add_column("version")
        table.add_column("advisory")
        table.add_column("repo")
        table.add_column("source")
        for h in hits:
            table.add_row(
                h.pkg.ecosystem,
                h.pkg.name,
                h.pkg.version,
                h.advisory_id,
                h.pkg.repo_path.name,
                h.pkg.source,
            )
        self.console.print(table)

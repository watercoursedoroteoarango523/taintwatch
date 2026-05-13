"""Persist every alert batch as a markdown file."""
from __future__ import annotations

import time
from pathlib import Path

from ..config import Config
from ..models import Hit
from ..paths import default_report_dir
from .base import AlertChannel


class ReportChannel(AlertChannel):
    name = "report"

    def __init__(self, cfg: Config) -> None:
        self.dir = cfg.alerts.report.dir or default_report_dir()

    def send(self, hits: list[Hit]) -> None:
        if not hits:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = self.dir / f"hits-{ts}.md"
        path.write_text(render_markdown(hits), encoding="utf-8")


def render_markdown(hits: list[Hit]) -> str:
    lines: list[str] = []
    lines.append(f"# taintwatch report — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"**{len(hits)} new compromised-package hit{'s' if len(hits) != 1 else ''} found.**")
    lines.append("")
    for h in hits:
        lines.append(f"## `{h.pkg.name}@{h.pkg.version}` ({h.pkg.ecosystem})")
        lines.append("")
        lines.append(f"- **Advisory:** `{h.advisory_id}` ({h.advisory.source})")
        if h.advisory.summary:
            lines.append(f"- **Summary:** {h.advisory.summary}")
        if h.advisory.severity:
            lines.append(f"- **Severity:** {h.advisory.severity}")
        lines.append(f"- **Repo:** `{h.pkg.repo_path}`")
        if h.pkg.lockfile_path:
            lines.append(f"- **Lockfile:** `{h.pkg.lockfile_path}`")
        if h.pkg.installed_path:
            lines.append(f"- **On disk:** `{h.pkg.installed_path}`")
        lines.append(f"- **Source:** {h.pkg.source}")
        if h.advisory.references:
            lines.append("- **References:**")
            for r in h.advisory.references:
                if r:
                    lines.append(f"  - {r}")
        lines.append("")
        lines.append("**What to do:**")
        lines.append("")
        if h.pkg.ecosystem == "npm":
            lines.append("```")
            lines.append(f"cd {h.pkg.repo_path}")
            lines.append("rm -rf node_modules")
            lines.append(f"npm uninstall {h.pkg.name}  # remove from package.json")
            lines.append(
                f"# Pin to a known-safe version once you've verified the advisory: npm install {h.pkg.name}@<safe-version>"
            )
            lines.append("npm install")
            lines.append("```")
        elif h.pkg.ecosystem == "PyPI":
            lines.append("```")
            lines.append(f"cd {h.pkg.repo_path}")
            lines.append(f"pip uninstall {h.pkg.name}")
            lines.append("# Recreate venv from a clean state and reinstall pinned-safe versions.")
            lines.append("```")
        else:
            lines.append("Review the advisory link, remove the affected version, and reinstall a vetted release.")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)

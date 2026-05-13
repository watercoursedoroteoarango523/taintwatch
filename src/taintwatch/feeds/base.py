from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod


class Fetcher(ABC):
    name: str

    @abstractmethod
    def update(self, conn: sqlite3.Connection, *, force: bool = False) -> int:
        """Pull latest data, upsert advisories into SQLite. Returns count upserted."""

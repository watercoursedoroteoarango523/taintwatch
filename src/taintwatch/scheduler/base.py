from __future__ import annotations

from abc import ABC, abstractmethod


class Scheduler(ABC):
    @abstractmethod
    def install(self, interval_minutes: int, *, dry_run: bool = False) -> str: ...

    @abstractmethod
    def uninstall(self) -> str: ...

    @abstractmethod
    def status(self) -> str: ...

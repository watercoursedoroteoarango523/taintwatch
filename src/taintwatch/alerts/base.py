from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Hit


class AlertChannel(ABC):
    name: str

    @abstractmethod
    def send(self, hits: list[Hit]) -> None: ...

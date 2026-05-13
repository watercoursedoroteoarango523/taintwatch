from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Hit
from .severity import Severity


class AlertChannel(ABC):
    name: str

    @abstractmethod
    def send(self, hits: list[Hit], severity: Severity = Severity.HIGH) -> None: ...

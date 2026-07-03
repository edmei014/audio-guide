from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceInfo:
    source_id: str
    display_name: str
    description: str
    default_channels: int


class AudioSource(ABC):
    """Physical audio input source."""

    @classmethod
    @abstractmethod
    def source_info(cls) -> SourceInfo:
        pass

    @property
    @abstractmethod
    def device(self) -> int:
        pass

    @property
    @abstractmethod
    def channels(self) -> int:
        pass

    @property
    def source_id(self) -> str:
        return self.source_info().source_id

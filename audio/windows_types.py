from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowsAudioDevice:
    name: str
    device_id: str

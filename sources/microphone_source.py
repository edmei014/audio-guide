from __future__ import annotations

from sources.base import AudioSource, SourceInfo


class MicrophoneSource(AudioSource):
    """Physical microphone input."""

    def __init__(self, device: int, channels: int = 1) -> None:
        self._device = device
        self._channels = channels

    @classmethod
    def source_info(cls) -> SourceInfo:
        return SourceInfo(
            source_id="microphone",
            display_name="Mikrofon",
            description="Physisches Mikrofon-Eingangsgerät",
            default_channels=1,
        )

    @property
    def device(self) -> int:
        return self._device

    @property
    def channels(self) -> int:
        return self._channels

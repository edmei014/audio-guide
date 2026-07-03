from __future__ import annotations

from sources.base import AudioSource, SourceInfo


class PlaybackSource(AudioSource):
    """System / loopback audio via virtual cable or similar device."""

    def __init__(self, device: int, channels: int = 2) -> None:
        self._device = device
        self._channels = channels

    @classmethod
    def source_info(cls) -> SourceInfo:
        return SourceInfo(
            source_id="playback",
            display_name="Playback",
            description="Systemton über VB-Cable oder vergleichbares Gerät",
            default_channels=2,
        )

    @property
    def device(self) -> int:
        return self._device

    @property
    def channels(self) -> int:
        return self._channels

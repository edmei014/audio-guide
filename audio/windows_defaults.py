"""Backward-compatible helpers built on WindowsAudioManager."""

from __future__ import annotations

from dataclasses import dataclass

from audio.windows_audio_manager import WindowsAudioManager
from audio.windows_device_mapping import names_refer_to_same_device

_manager = WindowsAudioManager()


@dataclass(frozen=True)
class SystemDefaultDevices:
    playback_name: str | None
    recording_name: str | None


def is_supported() -> bool:
    return _manager.is_supported()


def get_system_defaults() -> SystemDefaultDevices:
    playback = _manager.get_default_playback()
    recording = _manager.get_default_recording()
    return SystemDefaultDevices(
        playback_name=playback.name if playback else None,
        recording_name=recording.name if recording else None,
    )


def playback_already_default(device_name: str) -> bool:
    current = _manager.get_default_playback()
    if current is None:
        return False
    return names_refer_to_same_device(device_name, current.name)


def recording_already_default(device_name: str) -> bool:
    current = _manager.get_default_recording()
    if current is None:
        return False
    return names_refer_to_same_device(device_name, current.name)


def set_default_playback(device_name: str) -> bool:
    return _manager.set_default_playback(device_name)


def set_default_recording(device_name: str) -> bool:
    return _manager.set_default_recording(device_name)


def set_default_playback_if_needed(device_name: str) -> bool:
    if playback_already_default(device_name):
        return False
    return set_default_playback(device_name)


def set_default_recording_if_needed(device_name: str) -> bool:
    if recording_already_default(device_name):
        return False
    return set_default_recording(device_name)


def get_manager() -> WindowsAudioManager:
    return _manager

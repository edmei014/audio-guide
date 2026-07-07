"""Capture and restore Windows default audio devices across application lifetime."""

from __future__ import annotations

import atexit
import sys
from typing import TYPE_CHECKING

from audio.windows_audio_manager import WindowsAudioManager
from audio.windows_types import WindowsAudioDevice

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

_manager = WindowsAudioManager()

_startup_playback: WindowsAudioDevice | None = None
_playback_restored = False

_startup_recording: WindowsAudioDevice | None = None
_recording_restored = False

_installed = False


def capture_startup_defaults() -> WindowsAudioDevice | None:
    """Store the current Windows default playback device at startup."""
    global _startup_playback
    if not _manager.is_supported():
        _startup_playback = None
        return None

    _startup_playback = _manager.get_default_playback()
    return _startup_playback


def restore_startup_defaults() -> None:
    """Restore Windows playback default captured at startup. Safe to call multiple times."""
    global _playback_restored
    if _playback_restored or _startup_playback is None or not _manager.is_supported():
        return
    _playback_restored = True

    try:
        _manager.switch_default_playback(
            _startup_playback,
            operation="exit_restore_playback",
        )
    except Exception:
        pass


def capture_startup_recording_default() -> WindowsAudioDevice | None:
    """Store the current Windows default recording device at startup."""
    global _startup_recording
    if not _manager.is_supported():
        _startup_recording = None
        return None

    _startup_recording = _manager.get_default_recording()
    return _startup_recording


def restore_startup_recording_default() -> None:
    """Restore Windows recording default captured at startup. Safe to call multiple times."""
    global _recording_restored
    if _recording_restored or _startup_recording is None or not _manager.is_supported():
        return
    _recording_restored = True

    try:
        _manager.switch_default_recording(
            _startup_recording,
            operation="exit_restore_recording",
        )
    except Exception:
        pass


def install_exit_restore(app: QApplication | None = None) -> None:
    """Register restore hooks for normal exit, process exit, and unhandled exceptions."""
    global _installed
    if _installed:
        return
    _installed = True

    atexit.register(restore_startup_defaults)
    atexit.register(restore_startup_recording_default)

    original_excepthook = sys.excepthook

    def _restore_excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: object,
    ) -> None:
        restore_startup_defaults()
        restore_startup_recording_default()
        original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _restore_excepthook

    if app is not None:
        app.aboutToQuit.connect(restore_startup_defaults)
        app.aboutToQuit.connect(restore_startup_recording_default)

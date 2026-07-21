"""Persistent user configuration for Clear Audio v1.0."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RouteSettings:
    device_name: str | None = None
    device_hostapi: str | None = None
    noise_reduction_enabled: bool = False
    noise_reduction_strength: float = 1.0


@dataclass
class AppSettings:
    playback_output: RouteSettings | None = None
    microphone_input: RouteSettings | None = None
    microphone_output: RouteSettings | None = None
    saved_windows_playback: str | None = None
    saved_windows_recording: str | None = None
    first_run_setup_completed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AppSettings:
        def route(key: str) -> RouteSettings | None:
            raw = data.get(key)
            if not isinstance(raw, dict):
                return None
            return RouteSettings(
                device_name=raw.get("device_name"),
                device_hostapi=raw.get("device_hostapi"),
                noise_reduction_enabled=bool(raw.get("noise_reduction_enabled", False)),
                noise_reduction_strength=float(raw.get("noise_reduction_strength", 1.0)),
            )

        return cls(
            playback_output=route("playback_output"),
            microphone_input=route("microphone_input"),
            microphone_output=route("microphone_output"),
            saved_windows_playback=data.get("saved_windows_playback"),
            saved_windows_recording=data.get("saved_windows_recording"),
            first_run_setup_completed=bool(data.get("first_run_setup_completed", False)),
        )


def settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    return base / "Clear Audio" / "settings.json"


def load_settings() -> AppSettings:
    path = settings_path()
    if not path.exists():
        return AppSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return AppSettings.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return AppSettings()


def save_settings(settings: AppSettings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

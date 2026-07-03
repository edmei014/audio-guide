"""Audit log for Windows default device switches (Tidal DeviceSwitchLog equivalent)."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

from audio.windows_types import WindowsAudioDevice

_LOG_PATH = os.path.join(tempfile.gettempdir(), "AudioGuide-WindowsAudio.log")


@dataclass(frozen=True)
class RoleSwitchResult:
    role: str
    hresult: int
    message: str


@dataclass
class DeviceSwitchLog:
    operation: str
    previous_default: WindowsAudioDevice | None
    requested_default: WindowsAudioDevice
    verified_default: WindowsAudioDevice | None
    role_results: list[RoleSwitchResult] = field(default_factory=list)

    @property
    def all_roles_succeeded(self) -> bool:
        return all(result.hresult == 0 for result in self.role_results)

    @property
    def verified_match(self) -> bool:
        return (
            self.verified_default is not None
            and self.verified_default.device_id == self.requested_default.device_id
        )

    @property
    def changed(self) -> bool:
        return self.verified_match

    def format_text(self) -> str:
        lines = [
            self.operation,
            f"  Previous (Multimedia): {_format_endpoint(self.previous_default)}",
            f"  Target:                {_format_endpoint(self.requested_default)}",
        ]
        for result in self.role_results:
            status = "OK" if result.hresult == 0 else result.message
            lines.append(
                f"  SetDefaultEndpoint({result.role}): "
                f"0x{result.hresult & 0xFFFFFFFF:08X} {status}"
            )
        lines.append(f"  Verified:              {_format_endpoint(self.verified_default)}")
        lines.append(
            "  Result:                "
            + ("CHANGED" if self.changed else "NOT CHANGED")
        )
        return "\n".join(lines)


def _format_endpoint(device: WindowsAudioDevice | None) -> str:
    if device is None:
        return "(none)"
    return f"{device.name} [{device.device_id}]"


def append_switch_log(log: DeviceSwitchLog) -> None:
    with open(_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write("\n---\n")
        handle.write(log.format_text())
        handle.write("\n")


def log_path() -> str:
    return _LOG_PATH

"""Windows audio endpoint management — independent from the audio pipeline."""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from audio.windows_types import WindowsAudioDevice

DATA_FLOW_RENDER = 0
DATA_FLOW_CAPTURE = 1
_SETTLE_DELAY_SECONDS = 0.3
_SWITCH_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="win-audio")


class WindowsAudioManager:
    """Manage Windows default playback and recording devices via MMDevice API."""

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def get_default_playback(self) -> WindowsAudioDevice | None:
        if not self.is_supported():
            return None
        from audio._windows_mmdevice import get_default_multimedia_render

        return get_default_multimedia_render()

    def get_default_recording(self) -> WindowsAudioDevice | None:
        if not self.is_supported():
            return None
        from audio._windows_mmdevice import get_default_multimedia_capture

        return get_default_multimedia_capture()

    def enumerate_playback_devices(self) -> list[WindowsAudioDevice]:
        if not self.is_supported():
            return []
        from audio._windows_mmdevice import enumerate_active_render_devices

        return enumerate_active_render_devices()

    def enumerate_recording_devices(self) -> list[WindowsAudioDevice]:
        if not self.is_supported():
            return []
        from audio._windows_mmdevice import enumerate_active_capture_devices

        return enumerate_active_capture_devices()

    def set_default_playback(self, device: WindowsAudioDevice | str) -> bool:
        log = self.switch_default_playback(device, operation="set_default_playback")
        return log.changed if log is not None else False

    def set_default_recording(self, device: WindowsAudioDevice | str) -> bool:
        log = self.switch_default_recording(device, operation="set_default_recording")
        return log.changed if log is not None else False

    def switch_default_playback(
        self,
        device: WindowsAudioDevice | str,
        *,
        operation: str = "switch_default_playback",
    ):
        resolved = self._resolve_device(device, DATA_FLOW_RENDER)
        if resolved is None:
            return None
        return self._switch_default(resolved, DATA_FLOW_RENDER, operation)

    def switch_default_recording(
        self,
        device: WindowsAudioDevice | str,
        *,
        operation: str = "switch_default_recording",
    ):
        resolved = self._resolve_device(device, DATA_FLOW_CAPTURE)
        if resolved is None:
            return None
        return self._switch_default(resolved, DATA_FLOW_CAPTURE, operation)

    def _resolve_device(
        self,
        device: WindowsAudioDevice | str,
        data_flow: int,
    ) -> WindowsAudioDevice | None:
        if isinstance(device, WindowsAudioDevice):
            return device

        from audio.windows_device_mapping import map_to_windows_device

        endpoints = self._enumerate_for_flow(data_flow)
        mapping = map_to_windows_device(device, endpoints)
        if mapping is not None:
            return mapping.windows_device

        for entry in endpoints:
            if self._names_match(device, entry.name):
                return entry
        return None

    def _enumerate_for_flow(self, data_flow: int) -> list[WindowsAudioDevice]:
        if data_flow == DATA_FLOW_RENDER:
            return self.enumerate_playback_devices()
        return self.enumerate_recording_devices()

    def _switch_default(
        self,
        target: WindowsAudioDevice,
        data_flow: int,
        operation: str,
    ):
        if not self.is_supported():
            return None
        future = _SWITCH_EXECUTOR.submit(
            self._switch_default_worker,
            target,
            data_flow,
            operation,
        )
        log = future.result()
        from audio.windows_switch_log import append_switch_log

        append_switch_log(log)
        return log

    def _switch_default_worker(
        self,
        target: WindowsAudioDevice,
        data_flow: int,
        operation: str,
    ):
        from audio._windows_mmdevice import get_default_for_role
        from audio._windows_policy_config import (
            ROLE_COMMUNICATIONS,
            ROLE_CONSOLE,
            ROLE_MULTIMEDIA,
            create_policy_config,
        )
        from audio.windows_switch_log import DeviceSwitchLog, RoleSwitchResult

        self._co_initialize_worker()

        previous = get_default_for_role(data_flow, ROLE_MULTIMEDIA)
        role_results: list[RoleSwitchResult] = []
        policy_interface = "unavailable"

        try:
            policy = create_policy_config()
            policy_interface = type(policy).__name__
            for role, label in (
                (ROLE_CONSOLE, "eConsole"),
                (ROLE_MULTIMEDIA, "eMultimedia"),
                (ROLE_COMMUNICATIONS, "eCommunications"),
            ):
                hr = policy.SetDefaultEndpoint(target.device_id, role)
                message = "OK" if hr == 0 else _hresult_message(hr)
                role_results.append(
                    RoleSwitchResult(role=label, hresult=hr, message=message)
                )
        except OSError as exc:
            role_results.append(
                RoleSwitchResult(
                    role="PolicyConfig",
                    hresult=-1,
                    message=str(exc),
                )
            )

        time.sleep(_SETTLE_DELAY_SECONDS)
        verified = get_default_for_role(data_flow, ROLE_MULTIMEDIA)

        log = DeviceSwitchLog(
            operation=(
                f"{operation} [policy={policy_interface}]"
            ),
            previous_default=previous,
            requested_default=target,
            verified_default=verified,
            role_results=role_results,
        )
        return log

    @staticmethod
    def _co_initialize_worker() -> None:
        if sys.platform != "win32":
            return
        import ctypes

        # Match Tidal Task.Run: fresh MTA COM apartment on worker thread.
        hr = ctypes.windll.ole32.CoInitializeEx(None, 0)
        if hr not in (0, 1):
            ctypes.windll.ole32.CoInitialize(None)

    @staticmethod
    def _names_match(target: str, candidate: str) -> bool:
        left = " ".join(target.lower().split())
        right = " ".join(candidate.lower().split())
        return left == right or left in right or right in left


def _hresult_message(hr: int) -> str:
    if sys.platform != "win32":
        return f"0x{hr & 0xFFFFFFFF:08X}"
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.FormatMessageW.argtypes = [
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_wchar_p),
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    kernel32.FormatMessageW.restype = ctypes.c_ulong
    buffer = ctypes.c_wchar_p()
    flags = 0x00001000 | 0x00000200  # FORMAT_MESSAGE_FROM_SYSTEM | IGNORE_INSERTS
    length = kernel32.FormatMessageW(
        flags,
        None,
        hr & 0xFFFFFFFF,
        0,
        ctypes.byref(buffer),
        0,
        None,
    )
    if length == 0:
        return f"0x{hr & 0xFFFFFFFF:08X}"
    return buffer.value.strip() if buffer.value else f"0x{hr & 0xFFFFFFFF:08X}"


# Backward-compatible re-export
__all__ = ["WindowsAudioDevice", "WindowsAudioManager", "DATA_FLOW_RENDER", "DATA_FLOW_CAPTURE"]

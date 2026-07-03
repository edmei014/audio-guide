"""NAudio-equivalent MMDevice access for Windows audio endpoints."""

from __future__ import annotations

import sys

from audio.windows_types import WindowsAudioDevice

if sys.platform != "win32":
    raise ImportError("MMDevice access is only available on Windows")


def _co_initialize() -> None:
    import ctypes

    hr = ctypes.windll.ole32.CoInitializeEx(None, 0)
    # S_OK (0) or S_FALSE (1) — already initialized on this thread.
    if hr not in (0, 1):
        ctypes.windll.ole32.CoInitialize(None)


def get_default_multimedia_render() -> WindowsAudioDevice | None:
    """Match Tidal: GetDefaultAudioEndpoint(Render, Multimedia)."""
    _co_initialize()
    from pycaw.utils import AudioUtilities

    device = AudioUtilities.GetSpeakers()
    if device is None:
        return None
    return WindowsAudioDevice(name=device.FriendlyName, device_id=device.id)


def get_default_multimedia_capture() -> WindowsAudioDevice | None:
    _co_initialize()
    from pycaw.constants import EDataFlow, ERole
    from pycaw.pycaw import AudioUtilities
    import comtypes
    from comtypes import CLSCTX_INPROC_SERVER
    from pycaw.constants import CLSID_MMDeviceEnumerator
    from pycaw.api.mmdeviceapi import IMMDeviceEnumerator

    enumerator = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator,
        IMMDeviceEnumerator,
        CLSCTX_INPROC_SERVER,
    )
    endpoint = enumerator.GetDefaultAudioEndpoint(
        EDataFlow.eCapture.value,
        ERole.eMultimedia.value,
    )
    device = AudioUtilities.CreateDevice(endpoint)
    if device is None:
        return None
    return WindowsAudioDevice(name=device.FriendlyName, device_id=device.id)


def enumerate_active_render_devices() -> list[WindowsAudioDevice]:
    """Match Tidal: EnumerateAudioEndPoints(Render, Active)."""
    _co_initialize()
    from pycaw.constants import DEVICE_STATE
    from pycaw.pycaw import AudioUtilities, EDataFlow

    devices: list[WindowsAudioDevice] = []
    default = get_default_multimedia_render()
    default_id = default.device_id if default else None

    for device in AudioUtilities.GetAllDevices(
        EDataFlow.eRender.value,
        DEVICE_STATE.ACTIVE.value,
    ):
        devices.append(
            WindowsAudioDevice(name=device.FriendlyName, device_id=device.id)
        )

    devices.sort(
        key=lambda entry: (
            0 if entry.device_id == default_id else 1,
            entry.name.casefold(),
        )
    )
    return devices


def enumerate_active_capture_devices() -> list[WindowsAudioDevice]:
    _co_initialize()
    from pycaw.constants import DEVICE_STATE
    from pycaw.pycaw import AudioUtilities, EDataFlow

    devices: list[WindowsAudioDevice] = []
    for device in AudioUtilities.GetAllDevices(
        EDataFlow.eCapture.value,
        DEVICE_STATE.ACTIVE.value,
    ):
        devices.append(
            WindowsAudioDevice(name=device.FriendlyName, device_id=device.id)
        )
    devices.sort(key=lambda entry: entry.name.casefold())
    return devices


def get_default_for_role(data_flow: int, role: int) -> WindowsAudioDevice | None:
    _co_initialize()
    from pycaw.constants import EDataFlow, ERole
    import comtypes
    from comtypes import CLSCTX_INPROC_SERVER
    from pycaw.constants import CLSID_MMDeviceEnumerator
    from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
    from pycaw.utils import AudioUtilities

    flow = EDataFlow.eRender.value if data_flow == 0 else EDataFlow.eCapture.value
    enumerator = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator,
        IMMDeviceEnumerator,
        CLSCTX_INPROC_SERVER,
    )
    endpoint = enumerator.GetDefaultAudioEndpoint(flow, role)
    device = AudioUtilities.CreateDevice(endpoint)
    if device is None:
        return None
    return WindowsAudioDevice(name=device.FriendlyName, device_id=device.id)

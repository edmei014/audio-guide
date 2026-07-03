"""Debug Windows default playback switching against real OS state."""

from __future__ import annotations

import argparse
import sys
import time

from audio._windows_mmdevice import get_default_for_role
from audio._windows_policy_config import (
    ROLE_COMMUNICATIONS,
    ROLE_CONSOLE,
    ROLE_MULTIMEDIA,
    create_policy_config,
)
from audio.windows_audio_manager import WindowsAudioManager
from audio.windows_switch_log import log_path


def _role_name(role: int) -> str:
    return {0: "Console", 1: "Multimedia", 2: "Communications"}.get(role, str(role))


def _print_device(label: str, device) -> None:
    if device is None:
        print(f"{label}")
        print("  <none>")
        return
    print(f"{label}")
    print(f"  {device.name}")
    print(f"  id={device.device_id}")


def debug_switch(target_index: int | None, target_name: str | None) -> int:
    manager = WindowsAudioManager()
    devices = manager.enumerate_playback_devices()
    if not devices:
        print("No playback devices enumerated.")
        return 1

    print("=== Enumerated playback devices ===")
    for index, device in enumerate(devices):
        print(f"  [{index}] {device.name}")
        print(f"       id={device.device_id}")

    if target_index is not None:
        if target_index < 0 or target_index >= len(devices):
            print(f"Invalid index: {target_index}")
            return 1
        target = devices[target_index]
    elif target_name:
        target = manager._resolve_device(target_name, 0)
        if target is None:
            print(f"Could not resolve target name: {target_name!r}")
            return 1
    else:
        current = manager.get_default_playback()
        target = next(
            (
                device
                for device in devices
                if current is None or device.device_id != current.device_id
            ),
            devices[0],
        )

    print("\nCurrent default:")
    before = manager.get_default_playback()
    _print_device("", before)

    print("\nTarget:")
    _print_device("", target)

    print("\nCalling SetDefaultEndpoint...")
    try:
        policy = create_policy_config()
        print(f"  Policy interface: {type(policy).__name__}")
    except OSError as exc:
        print(f"  FAILED to create PolicyConfig: {exc}")
        return 1

    for role in (ROLE_CONSOLE, ROLE_MULTIMEDIA, ROLE_COMMUNICATIONS):
        hr = policy.SetDefaultEndpoint(target.device_id, role)
        status = "OK" if hr == 0 else f"FAILED 0x{hr & 0xFFFFFFFF:08X}"
        print(f"  SetDefaultEndpoint({_role_name(role)}): {status}")

    print("\nWaiting 300 ms...")
    time.sleep(0.3)

    print("\nCurrent default after call:")
    after = manager.get_default_playback()
    _print_device("", after)

    print("\nCurrent default by role (NAudio/pycaw read path):")
    for role in (ROLE_CONSOLE, ROLE_MULTIMEDIA, ROLE_COMMUNICATIONS):
        role_device = get_default_for_role(0, role)
        print(f"  {_role_name(role)}: {role_device.name if role_device else '<none>'}")
        if role_device:
            print(f"    id={role_device.device_id}")

    changed = after is not None and after.device_id == target.device_id
    print("\nResult:")
    print(f"  Changed = {changed}")

    if not changed:
        print("\nDiagnosis:")
        print("  - Windows MMDevice API still reports the previous default.")
        print("  - Check log file for app-level attempts:")
        print(f"    {log_path()}")
        print("  - Compare with Tidal Audio Switcher on the same target device.")
        print("  - If HRESULT is OK but device unchanged, PolicyConfig vtable mismatch")
        print("    or endpoint ID is wrong are the most likely causes.")

    return 0 if changed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, default=None, help="Target device index")
    parser.add_argument("--name", type=str, default=None, help="Target device name")
    args = parser.parse_args()
    return debug_switch(args.index, args.name)


if __name__ == "__main__":
    raise SystemExit(main())

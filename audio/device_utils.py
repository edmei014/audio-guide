from __future__ import annotations

import sounddevice as sd

from audio.devices import DeviceEntry


def device_fingerprint(devices: list[DeviceEntry]) -> tuple[tuple[str, str], ...]:
    """Stable identity for plug/unplug detection (ignores PortAudio indices)."""
    return tuple((entry.name, entry.hostapi) for entry in devices)


def find_device_index(
    devices: list[DeviceEntry],
    *,
    index: int | None = None,
    name: str | None = None,
    hostapi: str | None = None,
) -> int | None:
    if index is not None:
        for entry in devices:
            if entry.index == index:
                return entry.index
    if name is not None:
        for entry in devices:
            if entry.name == name and (hostapi is None or entry.hostapi == hostapi):
                return entry.index
        for entry in devices:
            if entry.name == name:
                return entry.index
    return None


def _is_vb_cable_render_name(name: str) -> bool:
    lowered = name.lower()
    return ("cable input" in lowered or "cable in" in lowered) and "output" not in lowered


def is_vb_cable_output_input(entry: DeviceEntry) -> bool:
    """VB-Cable capture endpoint (CABLE Output) used as an input in Clear Audio."""
    return entry.kind == "input" and "cable output" in entry.name.lower()


def is_vb_cable_input_output(entry: DeviceEntry) -> bool:
    """VB-Cable render endpoint (CABLE Input) used as an output in Clear Audio."""
    return entry.kind == "output" and _is_vb_cable_render_name(entry.name)


def find_matching_cable_input(
    outputs: list[DeviceEntry], cable_output_input: DeviceEntry
) -> DeviceEntry | None:
    """Find the VB-Cable playback endpoint (CABLE Input) for a CABLE Output input."""
    candidates = [entry for entry in outputs if _is_vb_cable_render_name(entry.name)]
    if not candidates:
        return None
    for hostapi in (cable_output_input.hostapi, "Windows WASAPI", "MME"):
        for entry in candidates:
            if entry.hostapi == hostapi:
                return entry
    return candidates[0]


def find_matching_cable_output(
    inputs: list[DeviceEntry], cable_input_output: DeviceEntry
) -> DeviceEntry | None:
    """Find the VB-Cable recording endpoint (CABLE Output) for a CABLE Input output."""
    candidates = [entry for entry in inputs if "cable output" in entry.name.lower()]
    if not candidates:
        return None
    for hostapi in (cable_input_output.hostapi, "Windows WASAPI", "MME"):
        for entry in candidates:
            if entry.hostapi == hostapi:
                return entry
    return candidates[0]


def find_device_entry(
    devices: list[DeviceEntry],
    *,
    name: str | None,
    hostapi: str | None,
) -> DeviceEntry | None:
    index = find_device_index(devices, name=name, hostapi=hostapi)
    if index is None:
        return None
    for entry in devices:
        if entry.index == index:
            return entry
    return None


def find_vb_cable_output_entry(inputs: list[DeviceEntry]) -> DeviceEntry | None:
    index = find_default_vb_cable_output(inputs)
    if index is None:
        return None
    for entry in inputs:
        if entry.index == index:
            return entry
    return None


def filter_playback_outputs(outputs: list[DeviceEntry]) -> list[DeviceEntry]:
    filtered = [
        entry
        for entry in outputs
        if "cable" not in entry.name.lower() and "vb-audio" not in entry.name.lower()
    ]
    return filtered or outputs


def filter_virtual_outputs(outputs: list[DeviceEntry]) -> list[DeviceEntry]:
    filtered = [entry for entry in outputs if _is_vb_cable_render_name(entry.name)]
    return filtered or outputs


def filter_microphone_inputs(inputs: list[DeviceEntry]) -> list[DeviceEntry]:
    filtered = [
        entry
        for entry in inputs
        if "cable" not in entry.name.lower() and "vb-audio" not in entry.name.lower()
    ]
    return filtered or inputs


def find_default_vb_cable_output(inputs: list[DeviceEntry]) -> int | None:
    for entry in inputs:
        if entry.hostapi == "Windows WASAPI" and "cable output" in entry.name.lower():
            return entry.index
    for entry in inputs:
        if "cable output" in entry.name.lower():
            return entry.index
    return inputs[0].index if inputs else None


def find_default_cable_input(outputs: list[DeviceEntry]) -> int | None:
    for entry in outputs:
        if _is_vb_cable_render_name(entry.name) and entry.hostapi == "Windows WASAPI":
            return entry.index
    for entry in outputs:
        if _is_vb_cable_render_name(entry.name):
            return entry.index
    return None


def find_default_microphone(inputs: list[DeviceEntry]) -> int | None:
    try:
        default_in = sd.default.device[0]
        if any(entry.index == default_in for entry in inputs):
            return default_in
    except (TypeError, IndexError, sd.PortAudioError):
        pass
    non_cable = [
        entry
        for entry in inputs
        if "cable" not in entry.name.lower() and "vb-audio" not in entry.name.lower()
    ]
    return non_cable[0].index if non_cable else (inputs[0].index if inputs else None)


def find_virtual_microphone_output(outputs: list[DeviceEntry]) -> DeviceEntry | None:
    """Best VB-Cable render endpoint for the microphone virtual output."""
    index = find_default_cable_input(outputs)
    if index is None:
        return None
    for entry in filter_virtual_outputs(outputs):
        if entry.index == index:
            return entry
    return None


def is_vb_cable_installed(
    inputs: list[DeviceEntry],
    outputs: list[DeviceEntry],
) -> bool:
    """Return True when VB-Cable capture and render endpoints are available."""
    return (
        find_vb_cable_output_entry(inputs) is not None
        and find_default_cable_input(outputs) is not None
    )


def find_default_speakers(outputs: list[DeviceEntry]) -> int | None:
    ifi_entries = [entry for entry in outputs if "ifi" in entry.name.lower()]
    for hostapi in ("MME", "Windows DirectSound", "Windows WASAPI"):
        for entry in ifi_entries:
            if entry.hostapi == hostapi and entry.default_sample_rate == 44100:
                return entry.index
    if ifi_entries:
        return ifi_entries[0].index
    try:
        return sd.default.device[1]
    except (TypeError, IndexError, sd.PortAudioError):
        return outputs[0].index if outputs else None

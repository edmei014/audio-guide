from __future__ import annotations

from dataclasses import dataclass

import sounddevice as sd

PREFERRED_HOSTAPIS: tuple[str, ...] = (
    "Windows WASAPI",
    "Windows DirectSound",
    "MME",
)
EXCLUDED_HOSTAPIS: tuple[str, ...] = ("Windows WDM-KS",)


@dataclass(frozen=True)
class StreamConfig:
    device: int
    sample_rate: int
    channels: int
    hostapi: str
    block_size: int


@dataclass(frozen=True)
class DeviceEntry:
    index: int
    name: str
    hostapi: str
    max_channels: int
    default_sample_rate: int
    kind: str


def hostapi_name(device_index: int, kind: str) -> str:
    info = sd.query_devices(device_index, kind=kind)
    return sd.query_hostapis(info["hostapi"])["name"]


def _max_channels(info: dict, kind: str) -> int:
    if kind == "input":
        return int(info["max_input_channels"])
    return int(info["max_output_channels"])


def _hostapi_priority(name: str) -> int:
    if name in EXCLUDED_HOSTAPIS:
        return 1000
    try:
        return PREFERRED_HOSTAPIS.index(name)
    except ValueError:
        return 500


def list_devices_fast(kind: str) -> list[DeviceEntry]:
    """List devices from PortAudio metadata only (no stream probing)."""
    devices = sd.query_devices()
    entries: list[DeviceEntry] = []

    for index, info in enumerate(devices):
        max_channels = _max_channels(info, kind)
        if max_channels <= 0:
            continue

        hostapi = sd.query_hostapis(info["hostapi"])["name"]
        if hostapi in EXCLUDED_HOSTAPIS:
            continue

        entries.append(
            DeviceEntry(
                index=index,
                name=info["name"],
                hostapi=hostapi,
                max_channels=max_channels,
                default_sample_rate=int(info["default_samplerate"]),
                kind=kind,
            )
        )

    entries.sort(
        key=lambda entry: (
            _hostapi_priority(entry.hostapi),
            entry.name.lower(),
            entry.index,
        )
    )
    return entries


def list_usable_devices(kind: str) -> list[DeviceEntry]:
    """List devices that can actually be opened (excludes broken WDM-KS entries)."""
    devices = sd.query_devices()
    entries: list[DeviceEntry] = []

    for index, info in enumerate(devices):
        max_channels = _max_channels(info, kind)
        if max_channels <= 0:
            continue

        hostapi = sd.query_hostapis(info["hostapi"])["name"]
        if hostapi in EXCLUDED_HOSTAPIS:
            continue

        default_sr = int(info["default_samplerate"])
        channels = min(2, max_channels)
        try:
            if not probe_stream(index, kind, default_sr, channels, block_size=480):
                continue
        except sd.PortAudioError:
            continue

        entries.append(
            DeviceEntry(
                index=index,
                name=info["name"],
                hostapi=hostapi,
                max_channels=max_channels,
                default_sample_rate=default_sr,
                kind=kind,
            )
        )

    entries.sort(
        key=lambda entry: (
            _hostapi_priority(entry.hostapi),
            entry.name.lower(),
            entry.index,
        )
    )
    return entries


def format_device_label(entry: DeviceEntry) -> str:
    return (
        f"{entry.name} — {entry.hostapi}, "
        f"{entry.default_sample_rate} Hz [{entry.index}]"
    )


def probe_stream(
    device: int,
    kind: str,
    sample_rate: int,
    channels: int,
    block_size: int,
) -> bool:
    kwargs: dict = {
        "device": device,
        "samplerate": sample_rate,
        "channels": channels,
        "blocksize": block_size,
        "dtype": "float32",
    }
    host = hostapi_name(device, kind)
    if host == "Windows WASAPI":
        kwargs["extra_settings"] = sd.WasapiSettings(exclusive=False)

    try:
        if kind == "input":
            stream = sd.InputStream(**kwargs)
        else:
            stream = sd.OutputStream(**kwargs)
        stream.start()
        stream.stop()
        stream.close()
        return True
    except sd.PortAudioError:
        return False


def resolve_stream_config(
    device: int,
    kind: str,
    preferred_rate: int,
    preferred_channels: int,
    block_size: int,
    reference_rate: int | None = None,
) -> StreamConfig:
    info = sd.query_devices(device, kind=kind)
    hostapi = sd.query_hostapis(info["hostapi"])["name"]
    rate_ref = reference_rate or preferred_rate

    if hostapi in EXCLUDED_HOSTAPIS:
        raise sd.PortAudioError(
            f"Gerät '{info['name']}' nutzt {hostapi} und wird nicht unterstützt. "
            "Bitte MME-, DirectSound- oder WASAPI-Eintrag wählen."
        )

    max_channels = _max_channels(info, kind)
    if max_channels <= 0:
        raise sd.PortAudioError(
            f"Gerät '{info['name']}' unterstützt keine {'Eingabe' if kind == 'input' else 'Ausgabe'}."
        )

    channels = max(1, min(preferred_channels, max_channels))
    default_rate = int(info["default_samplerate"])

    candidate_rates: list[int] = []
    for rate in (preferred_rate, default_rate, 48000, 44100):
        if rate not in candidate_rates:
            candidate_rates.append(rate)

    scaled_block = block_size
    for sample_rate in candidate_rates:
        if sample_rate != rate_ref:
            scaled_block = max(1, int(round(block_size * sample_rate / rate_ref)))
        else:
            scaled_block = block_size

        if probe_stream(device, kind, sample_rate, channels, scaled_block):
            return StreamConfig(
                device=device,
                sample_rate=sample_rate,
                channels=channels,
                hostapi=hostapi,
                block_size=scaled_block,
            )

    raise sd.PortAudioError(
        f"Keine gültige Konfiguration für '{info['name']}' "
        f"({channels} Kanäle, bevorzugt {preferred_rate} Hz)."
    )


def wasapi_settings(hostapi: str) -> sd.WasapiSettings | None:
    if hostapi == "Windows WASAPI":
        return sd.WasapiSettings(exclusive=False)
    return None

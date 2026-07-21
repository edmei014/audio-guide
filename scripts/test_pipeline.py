"""End-to-end test for Clear Audio v1 (noise reduction playback)."""

from __future__ import annotations

import sys
import time

from features.stable.config import default_playback_chain
from pipeline.session import AudioPlatform
from audio.device_utils import (
    find_default_speakers,
    find_default_vb_cable_output,
)


def main() -> int:
    print("=== Clear Audio v1.0 Test ===\n")

    platform = AudioPlatform()
    from audio.devices import list_usable_devices

    inputs = list_usable_devices("input")
    outputs = list_usable_devices("output")

    cable = find_default_vb_cable_output(inputs)
    speakers = find_default_speakers(outputs)
    if cable is None or speakers is None:
        print("ERROR: Geräte nicht gefunden.")
        return 1

    platform.playback.input_device = cable
    platform.playback.output_device = speakers
    platform.playback.chain = default_playback_chain()
    platform.sync_chain_slot_enabled(platform.playback.chain)

    try:
        from effects.noise_reduction import NoiseReductionEffect

        NoiseReductionEffect.ensure_available()
    except ImportError as exc:
        print(f"DeepFilterNet nicht verfügbar: {exc}")
        return 1

    print(f"Playback: in={cable} out={speakers}")
    platform.start_playback()
    time.sleep(3)
    metrics = platform.playback_metrics()
    platform.stop_all()

    if metrics is None:
        print("ERROR: Keine Metriken.")
        return 2

    print(
        f"OK — Latenz: {metrics.latency_ms:.1f} ms, "
        f"Verarbeitung: {metrics.process_ms:.1f} ms, "
        f"Drops: {metrics.dropped_blocks}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

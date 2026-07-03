"""Experimental VST chain test (requires requirements-experimental.txt)."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from features.experimental.config import default_playback_chain
from pipeline.session import AudioPlatform


def main() -> int:
    app = QApplication(sys.argv)
    platform = AudioPlatform()
    platform.playback.chain = default_playback_chain()

    path = r"C:\Users\edmei\Documents\Audio Guide\LoudMax_v1_47_WIN_VST3\LoudMax.vst3"
    try:
        entry = platform.vst_host.load_plugin(path)
    except (OSError, ValueError, ImportError) as exc:
        print(f"SKIP: {exc}")
        return 0

    platform.playback.chain.add_vst(entry.instance_id)
    processors = platform.vst_host.prepare_pipeline_processors(
        platform.playback.chain, "test"
    )
    print("Processors:", len(processors))
    platform.vst_host.release_pipeline_processors("test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Version 2+ experimental features (EQ, VST3, plugin UI)."""

from features.experimental.config import default_microphone_chain, default_playback_chain

ENABLE_EXPERIMENTAL_UI = False

__all__ = [
    "ENABLE_EXPERIMENTAL_UI",
    "default_playback_chain",
    "default_microphone_chain",
]

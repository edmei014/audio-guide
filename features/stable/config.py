"""Version 1.0 effect-chain defaults (noise reduction only)."""

from __future__ import annotations

from effects.equalizer import EqualizerSettings
from effects.noise_reduction import NoiseReductionSettings
from pipeline.effect_chain import ChainSlot, EffectChainConfig


def default_playback_chain() -> EffectChainConfig:
    """Playback chain for v1: NR enabled, no visible EQ/VST slots."""
    return EffectChainConfig(
        slots=[ChainSlot.builtin("noise_reduction", enabled=False)],
        noise_reduction=NoiseReductionSettings(enabled=False, strength=1.0, atten_lim=100.0),
        equalizer=EqualizerSettings(enabled=False, preset="Flat"),
    )


def default_microphone_chain() -> EffectChainConfig:
    """Microphone chain for v1: NR enabled, no visible EQ/VST slots."""
    return EffectChainConfig(
        slots=[ChainSlot.builtin("noise_reduction", enabled=False)],
        noise_reduction=NoiseReductionSettings(enabled=False, strength=1.0, atten_lim=100.0),
        equalizer=EqualizerSettings(enabled=False, preset="Flat"),
    )

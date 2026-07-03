"""Full effect-chain defaults for experimental / v2 builds."""

from __future__ import annotations

from pipeline.effect_chain import EffectChainConfig


def default_playback_chain() -> EffectChainConfig:
    return EffectChainConfig.default_playback()


def default_microphone_chain() -> EffectChainConfig:
    return EffectChainConfig.default_microphone()

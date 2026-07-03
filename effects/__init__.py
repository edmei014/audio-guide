from effects.base_effect import BaseEffect, EffectInfo
from effects.equalizer import EQ_PRESETS, EQ_BAND_FREQUENCIES, EqualizerEffect, EqualizerSettings
from effects.noise_reduction import NoiseReductionEffect, NoiseReductionSettings
from effects.vst_host import VST3Effect, VST3Host, VST3ParameterInfo, VST3PluginEntry

__all__ = [
    "BaseEffect",
    "EffectInfo",
    "EQ_BAND_FREQUENCIES",
    "EQ_PRESETS",
    "EqualizerEffect",
    "EqualizerSettings",
    "NoiseReductionEffect",
    "NoiseReductionSettings",
    "VST3Effect",
    "VST3Host",
    "VST3ParameterInfo",
    "VST3PluginEntry",
]

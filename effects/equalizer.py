from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from effects.base_effect import BaseEffect, BiquadFilter, EffectInfo, configure_peaking

EQ_BAND_FREQUENCIES: tuple[float, ...] = (
    31.0,
    62.0,
    125.0,
    250.0,
    500.0,
    1000.0,
    2000.0,
    4000.0,
    8000.0,
    16000.0,
)

EQ_PRESETS: dict[str, list[float]] = {
    "Flat": [0.0] * 10,
    "Voice Clarity": [1.0, 0.0, -1.5, -1.0, 0.0, 1.0, 2.5, 3.0, 2.0, 1.0],
    "Movies": [3.0, 2.0, 0.0, -1.0, -2.0, -2.0, -1.0, 0.0, 1.5, 2.5],
    "Gaming": [-2.0, 0.0, 0.0, 1.0, 2.0, 2.5, 3.0, 3.0, 2.0, 0.0],
    "Music": [2.0, 1.5, 0.5, -0.5, -1.0, 0.0, 1.0, 2.0, 2.5, 1.5],
    "Bass Boost": [6.0, 5.0, 4.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "Treble Boost": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 3.0, 5.0, 6.0],
    "Night Mode": [2.0, 1.5, 0.5, 0.0, 1.0, 2.0, 2.5, 0.0, -2.0, -4.0],
}


@dataclass
class EqualizerSettings:
    enabled: bool = False
    preset: str = "Flat"
    bands_db: list[float] = field(default_factory=lambda: [0.0] * 10)

    def apply_preset(self, preset_name: str) -> None:
        if preset_name not in EQ_PRESETS:
            raise ValueError(f"Unbekanntes Preset: {preset_name}")
        self.preset = preset_name
        self.bands_db = list(EQ_PRESETS[preset_name])


class EqualizerEffect(BaseEffect):
    """10-band parametric equalizer with presets."""

    def __init__(self, settings: EqualizerSettings | None = None) -> None:
        self._settings = settings or EqualizerSettings()
        self._filters = [BiquadFilter() for _ in EQ_BAND_FREQUENCIES]
        self._sample_rate = 0
        self._bands_key: tuple[float, ...] = tuple(self._settings.bands_db)

    @classmethod
    def effect_info(cls) -> EffectInfo:
        return EffectInfo(
            effect_id="equalizer",
            display_name="Equalizer",
            description="10-Band parametric EQ with presets",
            default_enabled=False,
        )

    @property
    def settings(self) -> EqualizerSettings:
        return self._settings

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._settings.enabled = value

    def _update_filters(self, sample_rate: int) -> None:
        bands_key = tuple(self._settings.bands_db)
        if sample_rate == self._sample_rate and bands_key == self._bands_key:
            return
        self._sample_rate = sample_rate
        self._bands_key = bands_key
        for index, frequency in enumerate(EQ_BAND_FREQUENCIES):
            configure_peaking(
                self._filters[index],
                sample_rate,
                frequency,
                self._settings.bands_db[index],
                q=1.2,
            )

    def process(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        if not self._settings.enabled or len(block) == 0:
            return block

        if all(abs(gain) < 0.01 for gain in self._settings.bands_db):
            return block

        self._update_filters(sample_rate)

        output = block
        for filter_ in self._filters:
            output = filter_.process(output)
        return output.astype(np.float32)

    def reset(self) -> None:
        for filter_ in self._filters:
            filter_.reset()

    def close(self) -> None:
        self.reset()

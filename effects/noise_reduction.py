from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from effects.base_effect import BaseEffect, EffectInfo
from models.deepfilternet import DeepFilterNetEnhancer


@dataclass
class NoiseReductionSettings:
    enabled: bool = True
    strength: float = 1.0
    atten_lim: float = 100.0


class NoiseReductionEffect(BaseEffect):
    """AI noise reduction via DeepFilterNet."""

    def __init__(
        self,
        settings: NoiseReductionSettings | None = None,
        log_level: str = "warn",
    ) -> None:
        self._settings = settings or NoiseReductionSettings()
        self._log_level = log_level
        self._processor: DeepFilterNetEnhancer | None = None
        self._dry_buffer: deque[float] = deque()

    @classmethod
    def effect_info(cls) -> EffectInfo:
        return EffectInfo(
            effect_id="noise_reduction",
            display_name="Noise Reduction",
            description="KI-Rauschunterdrückung (DeepFilterNet)",
            default_enabled=True,
        )

    @property
    def settings(self) -> NoiseReductionSettings:
        return self._settings

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._settings.enabled = value

    def _ensure_processor(self) -> DeepFilterNetEnhancer:
        if self._processor is None:
            self._processor = DeepFilterNetEnhancer(
                atten_lim=self._settings.atten_lim,
                log_level=self._log_level,
            )
        return self._processor

    def process(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        if not self._settings.enabled or len(block) == 0:
            return block.astype(np.float32, copy=False)

        processor = self._ensure_processor()
        if sample_rate != processor.sample_rate:
            return block

        self._dry_buffer.extend(block.tolist())
        wet = processor.process(block.astype(np.float32, copy=False))
        if len(wet) == 0:
            return np.empty(0, dtype=np.float32)

        dry_samples = []
        for _ in range(len(wet)):
            if not self._dry_buffer:
                break
            dry_samples.append(self._dry_buffer.popleft())
        dry = np.asarray(dry_samples, dtype=np.float32)
        length = min(len(dry), len(wet))
        if length == 0:
            return np.empty(0, dtype=np.float32)

        strength = float(np.clip(self._settings.strength, 0.0, 1.0))
        return (
            strength * wet[:length] + (1.0 - strength) * dry[:length]
        ).astype(np.float32)

    def reset(self) -> None:
        self._dry_buffer.clear()
        if self._processor is not None:
            self._processor.reset()

    def close(self) -> None:
        self._dry_buffer.clear()
        if self._processor is not None:
            self._processor.close()
            self._processor = None

    @classmethod
    def ensure_available(cls) -> None:
        DeepFilterNetEnhancer.ensure_available()

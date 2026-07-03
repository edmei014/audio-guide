from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class EffectInfo:
    effect_id: str
    display_name: str
    description: str
    default_enabled: bool = True


class BaseEffect(ABC):
    """Base class for all real-time audio effects."""

    @classmethod
    @abstractmethod
    def effect_info(cls) -> EffectInfo:
        pass

    @property
    def effect_id(self) -> str:
        return self.effect_info().effect_id

    @property
    @abstractmethod
    def enabled(self) -> bool:
        pass

    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool) -> None:
        pass

    @abstractmethod
    def process(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class BiquadFilter:
    """Direct Form II transposed biquad for streaming audio."""

    def __init__(self) -> None:
        self._b0 = 1.0
        self._b1 = 0.0
        self._b2 = 0.0
        self._a1 = 0.0
        self._a2 = 0.0
        self._z1 = 0.0
        self._z2 = 0.0

    def set_coefficients(
        self, b0: float, b1: float, b2: float, a0: float, a1: float, a2: float
    ) -> None:
        self._b0 = b0 / a0
        self._b1 = b1 / a0
        self._b2 = b2 / a0
        self._a1 = a1 / a0
        self._a2 = a2 / a0

    def reset(self) -> None:
        self._z1 = 0.0
        self._z2 = 0.0

    def process(self, samples: np.ndarray) -> np.ndarray:
        output = np.empty_like(samples)
        z1 = self._z1
        z2 = self._z2
        b0, b1, b2 = self._b0, self._b1, self._b2
        a1, a2 = self._a1, self._a2

        for index, sample in enumerate(samples):
            out = b0 * sample + z1
            z1 = b1 * sample - a1 * out + z2
            z2 = b2 * sample - a2 * out
            output[index] = out

        self._z1 = z1
        self._z2 = z2
        return output


def peaking_coefficients(
    sample_rate: int, frequency: float, gain_db: float, q: float = 1.0
) -> tuple[float, float, float, float, float, float]:
    amplitude = 10 ** (gain_db / 40.0)
    omega = 2.0 * math.pi * frequency / sample_rate
    sin_w = math.sin(omega)
    cos_w = math.cos(omega)
    alpha = sin_w / (2.0 * q)

    b0 = 1.0 + alpha * amplitude
    b1 = -2.0 * cos_w
    b2 = 1.0 - alpha * amplitude
    a0 = 1.0 + alpha / amplitude
    a1 = -2.0 * cos_w
    a2 = 1.0 - alpha / amplitude
    return b0, b1, b2, a0, a1, a2


def configure_peaking(
    filter_: BiquadFilter, sample_rate: int, frequency: float, gain_db: float, q: float = 1.0
) -> None:
    filter_.set_coefficients(*peaking_coefficients(sample_rate, frequency, gain_db, q))

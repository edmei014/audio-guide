from __future__ import annotations

import numpy as np


def resample_audio(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or len(samples) == 0:
        return samples.astype(np.float32, copy=False)

    dst_length = int(round(len(samples) * dst_rate / src_rate))
    if dst_length <= 0:
        return np.empty(0, dtype=np.float32)

    source_positions = np.arange(len(samples), dtype=np.float64)
    target_positions = np.linspace(0, len(samples) - 1, dst_length)
    return np.interp(target_positions, source_positions, samples).astype(np.float32)

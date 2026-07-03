from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd

from audio.devices import StreamConfig, wasapi_settings


class AudioCapture:
    """Low-latency input stream for a selected capture device."""

    def __init__(
        self,
        config: StreamConfig,
        on_block: Callable[[np.ndarray], None] | None = None,
    ) -> None:
        self.config = config
        self._on_block = on_block
        self._stream: sd.InputStream | None = None

    @property
    def sample_rate(self) -> int:
        return self.config.sample_rate

    @property
    def channels(self) -> int:
        return self.config.channels

    @property
    def block_size(self) -> int:
        return self.config.block_size

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            print(f"[Capture] {status}")

        if self.channels == 1:
            mono = indata[:, 0].copy()
        else:
            mono = indata.mean(axis=1, dtype=np.float32)

        if self._on_block is not None:
            self._on_block(mono)

    def start(self) -> None:
        if self._stream is not None:
            return

        extra = wasapi_settings(self.config.hostapi)
        self._stream = sd.InputStream(
            device=self.config.device,
            samplerate=self.config.sample_rate,
            blocksize=self.config.block_size,
            channels=self.config.channels,
            dtype="float32",
            callback=self._callback,
            extra_settings=extra,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return

        self._stream.stop()
        self._stream.close()
        self._stream = None

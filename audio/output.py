from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

import numpy as np
import sounddevice as sd

from audio.devices import StreamConfig, wasapi_settings


class AudioOutput:
    """Low-latency playback stream fed from an internal sample buffer."""

    def __init__(
        self,
        config: StreamConfig,
        max_buffer_samples: int = 48000,
    ) -> None:
        self.config = config
        self._buffer: deque[float] = deque(maxlen=max_buffer_samples)
        self._lock = Lock()
        self._stream: sd.OutputStream | None = None
        self.underruns = 0

    @property
    def sample_rate(self) -> int:
        return self.config.sample_rate

    @property
    def channels(self) -> int:
        return self.config.channels

    @property
    def block_size(self) -> int:
        return self.config.block_size

    def write(self, samples: np.ndarray) -> None:
        flat = samples.reshape(-1).tolist()
        with self._lock:
            self._buffer.extend(flat)

    def buffered_samples(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def _callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            print(f"[Output] {status}")

        with self._lock:
            available = len(self._buffer)
            if available >= frames:
                for index in range(frames):
                    outdata[index, 0] = self._buffer.popleft()
                if self.channels > 1:
                    outdata[:, 1] = outdata[:, 0]
            elif available > 0:
                for index in range(available):
                    outdata[index, 0] = self._buffer.popleft()
                outdata[available:frames, :] = 0.0
                if self.channels > 1 and available < frames:
                    outdata[available:frames, 1] = 0.0
                self.underruns += 1
            else:
                outdata.fill(0.0)
                self.underruns += 1

    def start(self) -> None:
        if self._stream is not None:
            return

        extra = wasapi_settings(self.config.hostapi)
        self._stream = sd.OutputStream(
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

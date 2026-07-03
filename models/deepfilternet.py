from __future__ import annotations

import sys

import numpy as np

try:
    from deepfilternet_rs import DeepFilterNetRealtime
except ImportError as exc:
    DeepFilterNetRealtime = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

_PYTHON_VERSION_HINT = (
    "DeepFilterNet benötigt Python 3.10, 3.11 oder 3.12 "
    f"(installiert: {sys.version_info.major}.{sys.version_info.minor}). "
    "Bitte eine unterstützte Python-Version installieren und ein venv anlegen."
)


class DeepFilterNetEnhancer:
    """Real-time DeepFilterNet backend via the Rust streaming runtime."""

    def __init__(
        self,
        atten_lim: float = 100.0,
        post_filter_beta: float = 0.0,
        compensate_delay: bool = True,
        log_level: str = "warn",
    ) -> None:
        if DeepFilterNetRealtime is None:
            if sys.version_info >= (3, 13):
                raise ImportError(_PYTHON_VERSION_HINT) from _IMPORT_ERROR
            raise ImportError(
                "deepfilternet-rs fehlt. Installation: pip install deepfilternet-rs"
            ) from _IMPORT_ERROR

        self._atten_lim = atten_lim
        self._post_filter_beta = post_filter_beta
        self._compensate_delay = compensate_delay
        self._log_level = log_level
        self._processor: DeepFilterNetRealtime | None = None
        self._create_processor()

    def _create_processor(self) -> None:
        if self._processor is not None:
            self._processor.close()

        self._processor = DeepFilterNetRealtime(
            model_path=None,
            atten_lim=self._atten_lim,
            log_level=self._log_level,
            compensate_delay=self._compensate_delay,
            post_filter_beta=self._post_filter_beta,
        )

    @property
    def name(self) -> str:
        return "DeepFilterNet"

    @property
    def sample_rate(self) -> int:
        return int(self._processor.sample_rate)

    @property
    def frame_length(self) -> int:
        return int(self._processor.frame_length)

    @property
    def atten_lim(self) -> float:
        return self._atten_lim

    @atten_lim.setter
    def atten_lim(self, value: float) -> None:
        self._atten_lim = float(np.clip(value, 0.0, 100.0))
        self._create_processor()

    def process(self, audio: np.ndarray) -> np.ndarray:
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32, copy=False)

        if audio.ndim != 1:
            audio = audio.reshape(-1)

        return self._processor.process_chunk(audio)

    def reset(self) -> None:
        self._create_processor()

    def close(self) -> None:
        if self._processor is not None:
            self._processor.close()
            self._processor = None

    @classmethod
    def ensure_available(cls) -> None:
        if DeepFilterNetRealtime is None:
            if sys.version_info >= (3, 13):
                raise ImportError(_PYTHON_VERSION_HINT) from _IMPORT_ERROR
            raise ImportError(
                "deepfilternet-rs fehlt. Installation: pip install deepfilternet-rs"
            ) from _IMPORT_ERROR

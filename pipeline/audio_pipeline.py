from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from audio.capture import AudioCapture
from audio.devices import resolve_stream_config
from audio.output import AudioOutput
from audio.resample import resample_audio
from effects.vst_host import VST3Host
from pipeline.effect_chain import EffectChainConfig, build_effect_chain
from sources.base import AudioSource

PROCESS_SAMPLE_RATE = 48000
PROCESS_BLOCK_SIZE = 480


@dataclass
class PipelineMetrics:
    process_ms: float = 0.0
    latency_ms: float = 0.0
    buffer_ms: float = 0.0
    underruns: int = 0
    dropped_blocks: int = 0
    is_running: bool = False


class AudioPipeline:
    """Single source -> effect chain -> output pipeline."""

    PREBUFFER_BLOCKS = 4

    def __init__(
        self,
        name: str,
        source: AudioSource,
        output_device: int,
        chain_config: EffectChainConfig,
        vst_host: VST3Host,
        process_rate: int = PROCESS_SAMPLE_RATE,
        process_block_size: int = PROCESS_BLOCK_SIZE,
        output_channels: int = 2,
    ) -> None:
        self.name = name
        self.source = source
        self.output_device = output_device
        self.chain_config = chain_config
        self.vst_host = vst_host
        self.process_rate = process_rate
        self.process_block_size = process_block_size

        self._input_config = resolve_stream_config(
            device=source.device,
            kind="input",
            preferred_rate=self.process_rate,
            preferred_channels=source.channels,
            block_size=self.process_block_size,
            reference_rate=self.process_rate,
        )

        output_info = sd.query_devices(output_device, kind="output")
        output_preferred_rate = int(output_info["default_samplerate"])
        self._output_config = resolve_stream_config(
            device=output_device,
            kind="output",
            preferred_rate=output_preferred_rate,
            preferred_channels=output_channels,
            block_size=self.process_block_size,
            reference_rate=self.process_rate,
        )

        self._input_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=32)
        self._metrics = PipelineMetrics()
        self._metrics_lock = threading.Lock()
        self._running = False
        self._ready = threading.Event()
        self._process_thread: threading.Thread | None = None
        self._vst_processors: dict[str, object] = {}

        self._capture = AudioCapture(
            config=self._input_config,
            on_block=self._on_capture_block,
        )
        self._output = AudioOutput(config=self._output_config)

    def get_metrics(self) -> PipelineMetrics:
        with self._metrics_lock:
            return PipelineMetrics(**self._metrics.__dict__)

    def _set_metrics(self, **kwargs: float | int | bool) -> None:
        with self._metrics_lock:
            for key, value in kwargs.items():
                setattr(self._metrics, key, value)

    def _on_capture_block(self, block: np.ndarray) -> None:
        if not self._running:
            return

        if self._capture.sample_rate != self.process_rate:
            block = resample_audio(block, self._capture.sample_rate, self.process_rate)

        try:
            self._input_queue.put_nowait(block)
        except queue.Full:
            with self._metrics_lock:
                self._metrics.dropped_blocks += 1

    def _process_loop(self) -> None:
        chain = build_effect_chain(
            self.chain_config, self.vst_host, self._vst_processors
        )
        prebuffer_count = 0

        try:
            while self._running:
                try:
                    block = self._input_queue.get(timeout=0.05)
                except queue.Empty:
                    continue

                start = time.perf_counter()
                try:
                    output = chain.process(block, self.process_rate)
                except Exception as exc:
                    print(f"[{self.name}] Effect chain error: {exc}")
                    output = block

                process_ms = (time.perf_counter() - start) * 1000.0
                if len(output) == 0:
                    continue

                if self._output.sample_rate != self.process_rate:
                    output = resample_audio(
                        output, self.process_rate, self._output.sample_rate
                    )

                if not self._ready.is_set():
                    prebuffer_count += 1
                    self._output.write(output)
                    if prebuffer_count >= self.PREBUFFER_BLOCKS:
                        self._ready.set()
                    continue

                self._output.write(output)
                buffer_ms = (
                    self._output.buffered_samples() / self._output.sample_rate * 1000.0
                )
                self._set_metrics(
                    process_ms=process_ms,
                    latency_ms=buffer_ms + process_ms,
                    buffer_ms=buffer_ms,
                    underruns=self._output.underruns,
                )
        finally:
            chain.close()

    def start(self) -> None:
        if self._running:
            return

        self._vst_processors = self.vst_host.prepare_pipeline_processors(
            self.chain_config, self.name
        )

        self._output.clear()
        self._ready.clear()
        with self._metrics_lock:
            self._metrics = PipelineMetrics(is_running=True)

        while not self._input_queue.empty():
            try:
                self._input_queue.get_nowait()
            except queue.Empty:
                break

        self._running = True
        self._process_thread = threading.Thread(
            target=self._process_loop,
            name=f"pipeline-{self.name}",
            daemon=True,
        )
        self._process_thread.start()
        self._capture.start()
        self._output.start()

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        self._ready.clear()

        if self._process_thread is not None:
            self._process_thread.join(timeout=2.0)
            self._process_thread = None

        self._capture.stop()
        self._output.stop()
        self.vst_host.release_pipeline_processors(self.name)
        self._vst_processors = {}
        self._set_metrics(is_running=False)

    def close(self) -> None:
        self.stop()

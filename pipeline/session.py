from __future__ import annotations

from dataclasses import dataclass, field

from effects.noise_reduction import NoiseReductionEffect
from effects.vst_host import VST3Host
from features.stable.config import default_microphone_chain, default_playback_chain
from pipeline.audio_pipeline import AudioPipeline, PipelineMetrics
from pipeline.effect_chain import EffectChainConfig
from sources.microphone_source import MicrophoneSource
from sources.playback_source import PlaybackSource


@dataclass
class PlaybackRouteConfig:
    input_device: int | None = None
    output_device: int | None = None
    chain: EffectChainConfig = field(default_factory=default_playback_chain)


@dataclass
class MicrophoneRouteConfig:
    input_device: int | None = None
    output_device: int | None = None
    chain: EffectChainConfig = field(default_factory=default_microphone_chain)


class AudioPlatform:
    """Manages playback and microphone pipelines with separate effect chains."""

    def __init__(self) -> None:
        self.vst_host = VST3Host()
        self.playback = PlaybackRouteConfig()
        self.microphone = MicrophoneRouteConfig()
        self._playback_pipeline: AudioPipeline | None = None
        self._microphone_pipeline: AudioPipeline | None = None

    @property
    def playback_running(self) -> bool:
        return (
            self._playback_pipeline is not None
            and self._playback_pipeline.get_metrics().is_running
        )

    @property
    def microphone_running(self) -> bool:
        return (
            self._microphone_pipeline is not None
            and self._microphone_pipeline.get_metrics().is_running
        )

    def start_playback(self) -> None:
        if self.playback_running:
            return
        if self.playback.input_device is None or self.playback.output_device is None:
            raise ValueError("Playback-Eingang und -Ausgang müssen gewählt sein.")

        if self.playback.chain.noise_reduction.enabled:
            NoiseReductionEffect.ensure_available()

        source = PlaybackSource(device=self.playback.input_device)
        self._playback_pipeline = AudioPipeline(
            name="playback",
            source=source,
            output_device=self.playback.output_device,
            chain_config=self.playback.chain,
            vst_host=self.vst_host,
        )
        self._playback_pipeline.start()

    def stop_playback(self) -> None:
        if self._playback_pipeline is not None:
            self._playback_pipeline.close()
            self._playback_pipeline = None

    def start_microphone(self) -> None:
        if self.microphone_running:
            return
        if self.microphone.input_device is None or self.microphone.output_device is None:
            raise ValueError("Mikrofon-Eingang und virtuelles Ausgang müssen gewählt sein.")

        if self.microphone.chain.noise_reduction.enabled:
            NoiseReductionEffect.ensure_available()

        source = MicrophoneSource(device=self.microphone.input_device)
        self._microphone_pipeline = AudioPipeline(
            name="microphone",
            source=source,
            output_device=self.microphone.output_device,
            chain_config=self.microphone.chain,
            vst_host=self.vst_host,
        )
        self._microphone_pipeline.start()

    def stop_microphone(self) -> None:
        if self._microphone_pipeline is not None:
            self._microphone_pipeline.close()
            self._microphone_pipeline = None

    def stop_all(self) -> None:
        self.stop_playback()
        self.stop_microphone()

    def playback_metrics(self) -> PipelineMetrics | None:
        if self._playback_pipeline is None:
            return None
        return self._playback_pipeline.get_metrics()

    def microphone_metrics(self) -> PipelineMetrics | None:
        if self._microphone_pipeline is None:
            return None
        return self._microphone_pipeline.get_metrics()

    def sync_chain_slot_enabled(self, chain: EffectChainConfig) -> None:
        """Sync slot enabled flags with effect settings objects."""
        for slot in chain.slots:
            if slot.effect_type == "noise_reduction":
                slot.enabled = chain.noise_reduction.enabled
            elif slot.effect_type == "equalizer":
                slot.enabled = chain.equalizer.enabled

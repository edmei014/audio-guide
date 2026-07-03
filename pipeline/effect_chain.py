from __future__ import annotations

import logging

import uuid
from dataclasses import dataclass, field

import numpy as np

from effects.base_effect import BaseEffect
from effects.equalizer import EqualizerEffect, EqualizerSettings
from effects.noise_reduction import NoiseReductionEffect, NoiseReductionSettings
from effects.vst_host import VST3Effect, VST3Host
from effects.vst_host import _VST3RuntimeProcessor as VST3RuntimeProcessor

logger = logging.getLogger(__name__)


@dataclass
class ChainSlot:
    """Single slot in an effect chain (builtin or VST)."""

    slot_id: str
    kind: str  # "builtin" | "vst"
    effect_type: str  # noise_reduction, equalizer, or vst instance_id
    enabled: bool = True

    @staticmethod
    def builtin(effect_type: str, enabled: bool = True) -> ChainSlot:
        return ChainSlot(
            slot_id=uuid.uuid4().hex,
            kind="builtin",
            effect_type=effect_type,
            enabled=enabled,
        )

    @staticmethod
    def vst(instance_id: str, enabled: bool = True) -> ChainSlot:
        return ChainSlot(
            slot_id=uuid.uuid4().hex,
            kind="vst",
            effect_type=instance_id,
            enabled=enabled,
        )


@dataclass
class EffectChainConfig:
    """Mutable configuration for a source-specific effect chain."""

    slots: list[ChainSlot] = field(default_factory=list)
    noise_reduction: NoiseReductionSettings = field(default_factory=NoiseReductionSettings)
    equalizer: EqualizerSettings = field(default_factory=EqualizerSettings)

    @classmethod
    def default_playback(cls) -> EffectChainConfig:
        """Full chain with EQ slot — use features.experimental.config in v2 builds."""
        return cls(
            slots=[
                ChainSlot.builtin("noise_reduction", enabled=True),
                ChainSlot.builtin("equalizer", enabled=False),
            ],
            noise_reduction=NoiseReductionSettings(enabled=True, strength=1.0, atten_lim=100.0),
            equalizer=EqualizerSettings(enabled=False, preset="Flat"),
        )

    @classmethod
    def default_microphone(cls) -> EffectChainConfig:
        config = cls.default_playback()
        config.equalizer.apply_preset("Voice Clarity")
        return config

    def add_vst(self, instance_id: str) -> ChainSlot:
        slot = ChainSlot.vst(instance_id, enabled=True)
        self.slots.append(slot)
        logger.debug(
            "VST-Slot erzeugt: instance_id=%s slot_id=%s gesamt=%d",
            instance_id,
            slot.slot_id,
            len(self.slots),
        )
        return slot

    def remove_slot(self, slot_id: str) -> None:
        self.slots = [slot for slot in self.slots if slot.slot_id != slot_id]

    def move_slot(self, slot_id: str, direction: int) -> None:
        for index, slot in enumerate(self.slots):
            if slot.slot_id != slot_id:
                continue
            new_index = index + direction
            if 0 <= new_index < len(self.slots):
                self.slots[index], self.slots[new_index] = (
                    self.slots[new_index],
                    self.slots[index],
                )
            return

    def slot_labels(self, vst_names: dict[str, str] | None = None) -> list[str]:
        labels = []
        names = vst_names or {}
        for slot in self.slots:
            if slot.kind == "builtin":
                labels.append(slot.effect_type.replace("_", " ").title())
            else:
                labels.append(names.get(slot.effect_type, "VST3 Plugin"))
        return labels


class EffectChain:
    """Ordered, configurable real-time effect processing chain."""

    def __init__(self, effects: list[BaseEffect]) -> None:
        self._effects = effects

    @property
    def effects(self) -> list[BaseEffect]:
        return list(self._effects)

    def process(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        output = block
        for effect in self._effects:
            if not effect.enabled:
                continue
            processed = effect.process(output, sample_rate)
            if len(processed) == 0:
                return np.empty(0, dtype=np.float32)
            output = processed
        return output

    def reset(self) -> None:
        for effect in self._effects:
            effect.reset()

    def close(self) -> None:
        for effect in self._effects:
            effect.close()


def build_effect_chain(
    config: EffectChainConfig,
    vst_host: VST3Host,
    vst_processors: dict[str, VST3RuntimeProcessor] | None = None,
) -> EffectChain:
    """Build runtime chain. Built-in effects are created here; VST uses pre-loaded runtimes."""
    builtins: dict[str, BaseEffect] = {
        "noise_reduction": NoiseReductionEffect(settings=config.noise_reduction),
        "equalizer": EqualizerEffect(settings=config.equalizer),
    }
    vst_map = vst_processors or {}

    ordered: list[BaseEffect] = []
    for slot in config.slots:
        if slot.kind == "builtin":
            effect = builtins.get(slot.effect_type)
            if effect is None:
                continue
            effect.enabled = slot.enabled
            ordered.append(effect)
        elif slot.kind == "vst":
            runtime = vst_map.get(slot.slot_id)
            if runtime is None:
                logger.warning(
                    "VST-Slot %s ohne Runtime-Instanz – Pipeline neu starten?",
                    slot.slot_id,
                )
                continue
            try:
                vst_effect = VST3Effect(vst_host, slot.effect_type, runtime)
            except (KeyError, ValueError, ImportError, OSError) as exc:
                logger.error("VST-Slot übersprungen (%s): %s", slot.effect_type, exc)
                continue
            vst_effect.enabled = slot.enabled
            ordered.append(vst_effect)

    return EffectChain(ordered)

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from pedalboard import load_plugin

from effects.base_effect import BaseEffect, EffectInfo

logger = logging.getLogger(__name__)


def _assert_main_thread(action: str) -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError(f"{action} must run on the main thread.")


@dataclass(frozen=True)
class VST3ParameterInfo:
    name: str
    label: str
    minimum: float
    maximum: float
    value: float
    units: str | None = None


@dataclass
class VST3PluginEntry:
    instance_id: str
    path: str
    name: str
    enabled: bool = True
    loaded: bool = False
    error: str | None = None
    is_effect: bool = True
    parameter_values: dict[str, float] = field(default_factory=dict)


class _VST3RuntimeProcessor:
    """Wraps a main-thread-loaded Pedalboard plugin for audio-thread process() calls."""

    def __init__(self, plugin: Any, entry: VST3PluginEntry) -> None:
        if plugin.is_instrument and not plugin.is_effect:
            raise ValueError(
                f"'{entry.name}' ist ein Instrument-Plugin und wird nicht unterstützt."
            )
        self._plugin = plugin
        self._enabled = entry.enabled
        self._overflow = np.empty(0, dtype=np.float32)
        self._apply_parameter_values(entry.parameter_values)

    def _apply_parameter_values(self, values: dict[str, float]) -> None:
        for name, value in values.items():
            if name not in self._plugin.parameters:
                continue
            try:
                setattr(self._plugin, name, value)
            except (AttributeError, ValueError, TypeError):
                try:
                    self._plugin.parameters[name].raw_value = float(np.clip(value, 0.0, 1.0))
                except (AttributeError, ValueError, TypeError):
                    pass

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def set_parameter(self, name: str, value: float) -> None:
        if name not in self._plugin.parameters:
            raise KeyError(name)
        setattr(self._plugin, name, value)

    def process(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        if not self._enabled or len(block) == 0:
            return block.astype(np.float32, copy=False)

        if len(self._overflow) >= len(block):
            output = self._overflow[: len(block)].copy()
            self._overflow = self._overflow[len(block) :]
            return output

        in_channels = getattr(self._plugin, "in_channels", None) or 2
        in_channels = max(1, int(in_channels))
        if in_channels == 1:
            audio_in = block.reshape(1, -1).astype(np.float32, copy=False)
        else:
            audio_in = np.stack([block, block], axis=0).astype(np.float32, copy=False)

        block_size = max(len(block), 512)
        audio_out = self._plugin.process(
            audio_in,
            float(sample_rate),
            buffer_size=block_size,
            reset=False,
        )

        mono = _to_mono(audio_out)
        if len(mono) < len(block):
            padded = np.zeros(len(block), dtype=np.float32)
            padded[: len(mono)] = mono
            return padded
        if len(mono) > len(block):
            self._overflow = mono[len(block) :].copy()
            return mono[: len(block)].astype(np.float32)
        return mono.astype(np.float32, copy=False)

    def reset(self) -> None:
        self._overflow = np.empty(0, dtype=np.float32)
        self._plugin.reset()

    def close(self) -> None:
        self._overflow = np.empty(0, dtype=np.float32)
        self._plugin = None


def _to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float32, copy=False)
    if audio.shape[0] == 1:
        return audio[0].astype(np.float32, copy=False)
    return audio.mean(axis=0).astype(np.float32)


def _read_parameter_info(plugin: Any) -> list[VST3ParameterInfo]:
    parameters: list[VST3ParameterInfo] = []
    for name, param in plugin.parameters.items():
        try:
            value = float(param)
        except (TypeError, ValueError):
            value = float(param.raw_value)
        minimum = getattr(param, "minimum", 0.0)
        maximum = getattr(param, "maximum", 1.0)
        try:
            minimum = float(minimum) if minimum is not None else 0.0
        except (TypeError, ValueError):
            minimum = 0.0
        try:
            maximum = float(maximum) if maximum is not None else 1.0
        except (TypeError, ValueError):
            maximum = 1.0
        label = getattr(param, "label", None) or name
        units = getattr(param, "units", None)
        parameters.append(
            VST3ParameterInfo(
                name=name,
                label=str(label),
                minimum=minimum,
                maximum=maximum,
                value=value,
                units=str(units) if units else None,
            )
        )
    return parameters


class VST3Host:
    """VST3 plugin host powered by Spotify Pedalboard (JUCE)."""

    def __init__(self) -> None:
        self._plugins: dict[str, VST3PluginEntry] = {}
        self._parameter_cache: dict[str, list[VST3ParameterInfo]] = {}
        self._gui_plugins: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._active_runtimes: dict[str, list[_VST3RuntimeProcessor]] = {}
        self._pipeline_processors: dict[str, dict[str, _VST3RuntimeProcessor]] = {}

    @property
    def plugins(self) -> list[VST3PluginEntry]:
        with self._lock:
            return list(self._plugins.values())

    def discover_plugins(self, directory: str | Path) -> list[Path]:
        root = Path(directory)
        if not root.is_dir():
            return []
        return sorted(root.rglob("*.vst3"))

    def load_plugin(self, path: str) -> VST3PluginEntry:
        """Load and validate a plugin on the main thread (GUI)."""
        _assert_main_thread("VST3 plugin loading")
        plugin_path = Path(path)
        if not plugin_path.exists():
            raise FileNotFoundError(f"VST3-Datei nicht gefunden: {path}")

        suffix = plugin_path.suffix.lower()
        if suffix != ".vst3":
            raise ValueError("Nur .vst3-Dateien werden unterstützt.")

        resolved = str(plugin_path.resolve())
        try:
            plugin = load_plugin(resolved)
        except ImportError as exc:
            raise ValueError(f"Plugin konnte nicht geladen werden: {exc}") from exc

        if plugin.is_instrument and not plugin.is_effect:
            raise ValueError(
                f"'{plugin.name}' ist ein Instrument-Plugin. "
                "Bitte ein Effekt-Plugin (FX) laden."
            )

        display_name = plugin.descriptive_name or plugin.name or plugin_path.stem
        param_infos = _read_parameter_info(plugin)
        param_values = {info.name: info.value for info in param_infos}

        instance_id = uuid.uuid4().hex
        entry = VST3PluginEntry(
            instance_id=instance_id,
            path=resolved,
            name=str(display_name),
            loaded=True,
            error=None,
            is_effect=bool(plugin.is_effect),
            parameter_values=param_values,
        )

        with self._lock:
            self._plugins[instance_id] = entry
            self._parameter_cache[instance_id] = param_infos
            self._gui_plugins[instance_id] = plugin

        logger.info(
            "Plugin geladen (main thread): name=%s instance_id=%s",
            entry.name,
            entry.instance_id,
        )
        return entry

    def prepare_pipeline_processors(
        self, config: Any, pipeline_id: str
    ) -> dict[str, _VST3RuntimeProcessor]:
        """Create per-pipeline VST instances on the main thread before audio starts."""
        _assert_main_thread("VST3 pipeline preparation")
        processors: dict[str, _VST3RuntimeProcessor] = {}

        with self._lock:
            for slot in config.slots:
                if slot.kind != "vst":
                    continue
                entry = self._plugins.get(slot.effect_type)
                if entry is None:
                    logger.warning(
                        "VST-Slot %s verweist auf unbekanntes Plugin %s",
                        slot.slot_id,
                        slot.effect_type,
                    )
                    continue
                try:
                    plugin = load_plugin(entry.path)
                except ImportError as exc:
                    logger.error(
                        "VST %s konnte nicht für Pipeline %s geladen werden: %s",
                        entry.name,
                        pipeline_id,
                        exc,
                    )
                    continue

                runtime = _VST3RuntimeProcessor(plugin, entry)
                runtime.enabled = slot.enabled
                processors[slot.slot_id] = runtime
                self._active_runtimes.setdefault(slot.effect_type, []).append(runtime)

            self._pipeline_processors[pipeline_id] = processors

        logger.info(
            "Pipeline %s: %d VST-Runtime-Instanz(en) auf Main Thread vorbereitet",
            pipeline_id,
            len(processors),
        )
        return processors

    def release_pipeline_processors(self, pipeline_id: str) -> None:
        with self._lock:
            processors = self._pipeline_processors.pop(pipeline_id, {})
            for runtime in processors.values():
                for runtimes in self._active_runtimes.values():
                    if runtime in runtimes:
                        runtimes.remove(runtime)
                runtime.close()

    def unload_plugin(self, instance_id: str) -> None:
        with self._lock:
            self._plugins.pop(instance_id, None)
            self._parameter_cache.pop(instance_id, None)
            self._gui_plugins.pop(instance_id, None)
            self._active_runtimes.pop(instance_id, None)

    def set_enabled(self, instance_id: str, enabled: bool) -> None:
        with self._lock:
            entry = self._plugins.get(instance_id)
            if entry is not None:
                entry.enabled = enabled
            for runtime in self._active_runtimes.get(instance_id, []):
                runtime.enabled = enabled

    def get_plugin(self, instance_id: str) -> VST3PluginEntry | None:
        with self._lock:
            return self._plugins.get(instance_id)

    def get_parameters(self, instance_id: str) -> list[VST3ParameterInfo]:
        with self._lock:
            cached = self._parameter_cache.get(instance_id, [])
            entry = self._plugins.get(instance_id)
            if entry is None:
                return []
            result: list[VST3ParameterInfo] = []
            for info in cached:
                value = entry.parameter_values.get(info.name, info.value)
                result.append(
                    VST3ParameterInfo(
                        name=info.name,
                        label=info.label,
                        minimum=info.minimum,
                        maximum=info.maximum,
                        value=value,
                        units=info.units,
                    )
                )
            return result

    def set_parameter(self, instance_id: str, name: str, value: float) -> None:
        with self._lock:
            entry = self._plugins.get(instance_id)
            if entry is None:
                raise KeyError(instance_id)
            entry.parameter_values[name] = value

            gui_plugin = self._gui_plugins.get(instance_id)
            if gui_plugin is not None and name in gui_plugin.parameters:
                try:
                    setattr(gui_plugin, name, value)
                except (AttributeError, ValueError, TypeError):
                    pass

            for runtime in self._active_runtimes.get(instance_id, []):
                runtime.set_parameter(name, value)

    def release_runtime_processor(
        self, instance_id: str, runtime: _VST3RuntimeProcessor
    ) -> None:
        with self._lock:
            runtimes = self._active_runtimes.get(instance_id, [])
            if runtime in runtimes:
                runtimes.remove(runtime)
            runtime.close()


class VST3Effect(BaseEffect):
    """Effect-chain wrapper using a main-thread-prepared runtime processor."""

    def __init__(
        self,
        host: VST3Host,
        instance_id: str,
        runtime: _VST3RuntimeProcessor,
    ) -> None:
        self._host = host
        self._instance_id = instance_id
        self._runtime = runtime

    @classmethod
    def effect_info(cls) -> EffectInfo:
        return EffectInfo(
            effect_id="vst3",
            display_name="VST3 Plugin",
            description="Externes VST3-Plugin (Pedalboard)",
            default_enabled=True,
        )

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @property
    def display_name(self) -> str:
        entry = self._host.get_plugin(self._instance_id)
        return entry.name if entry else "VST3"

    @property
    def enabled(self) -> bool:
        return self._runtime.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._runtime.enabled = value
        self._host.set_enabled(self._instance_id, value)

    def process(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        return self._runtime.process(block, sample_rate)

    def reset(self) -> None:
        self._runtime.reset()

    def close(self) -> None:
        # Runtime lifecycle is managed by VST3Host.release_pipeline_processors().
        pass

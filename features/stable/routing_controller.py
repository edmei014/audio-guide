"""Automatic playback and microphone routing with Windows device management."""

from __future__ import annotations

from dataclasses import dataclass

from audio.devices import DeviceEntry
from audio.device_utils import (
    find_matching_cable_input,
    find_matching_cable_output,
    find_vb_cable_output_entry,
    is_vb_cable_input_output,
)
from audio.windows_defaults import (
    get_manager,
    get_system_defaults,
    is_supported as windows_defaults_supported,
)
from effects.noise_reduction import NoiseReductionEffect
from features.stable.settings_store import AppSettings, RouteSettings, save_settings
from pipeline.session import AudioPlatform


@dataclass
class RoutingResult:
    playback_error: str | None = None
    microphone_error: str | None = None
    windows_playback_hint: str | None = None
    windows_recording_hint: str | None = None


class RoutingController:
    """Applies routing only in response to explicit configuration changes."""

    def __init__(
        self,
        platform: AudioPlatform,
        inputs: list[DeviceEntry],
        outputs: list[DeviceEntry],
        settings: AppSettings,
    ) -> None:
        self._platform = platform
        self._inputs = inputs
        self._outputs = outputs
        self._settings = settings

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update_device_lists(
        self,
        inputs: list[DeviceEntry],
        outputs: list[DeviceEntry],
    ) -> None:
        self._inputs = inputs
        self._outputs = outputs

    def _update_playback_chain(self, *, nr_enabled: bool, strength: float) -> None:
        chain = self._platform.playback.chain
        chain.noise_reduction.enabled = nr_enabled
        chain.noise_reduction.strength = strength
        self._platform.sync_chain_slot_enabled(chain)

    def _playback_cable_capture(self) -> DeviceEntry | None:
        return find_vb_cable_output_entry(self._inputs)

    def restart_playback(
        self,
        output: DeviceEntry | None,
        *,
        nr_enabled: bool,
        strength: float,
    ) -> RoutingResult:
        """Restart the playback pipeline when the output device changes."""
        result = RoutingResult()
        self._update_playback_chain(nr_enabled=nr_enabled, strength=strength)
        self._platform.stop_playback()

        if output is None:
            result.playback_error = "Select a playback output device."
            self._persist_playback(output, nr_enabled, strength)
            return result

        cable_capture = self._playback_cable_capture()
        if cable_capture is None:
            result.playback_error = (
                "VB-Cable is not available. Install VB-Audio Virtual Cable "
                "to use playback processing."
            )
            self._persist_playback(output, nr_enabled, strength)
            return result

        self._platform.playback.input_device = cable_capture.index
        self._platform.playback.output_device = output.index
        try:
            if nr_enabled:
                NoiseReductionEffect.ensure_available()
            self._platform.start_playback()
        except Exception as exc:
            result.playback_error = str(exc)

        self._persist_playback(output, nr_enabled, strength)
        return result

    def set_playback_routing(
        self,
        output: DeviceEntry | None,
        *,
        nr_enabled: bool,
        strength: float,
        apply_windows: bool = True,
    ) -> RoutingResult:
        """Toggle NR bypass and Windows routing without restarting the pipeline."""
        result = RoutingResult()
        self._update_playback_chain(nr_enabled=nr_enabled, strength=strength)

        if nr_enabled:
            try:
                NoiseReductionEffect.ensure_available()
            except ImportError as exc:
                result.playback_error = str(exc)
                self._persist_playback(output, nr_enabled, strength)
                return result

        if output is None:
            result.playback_error = "Select a playback output device."
            self._persist_playback(output, nr_enabled, strength)
            return result

        if apply_windows and windows_defaults_supported():
            if nr_enabled:
                cable_capture = self._playback_cable_capture()
                cable_render = (
                    find_matching_cable_input(self._outputs, cable_capture)
                    if cable_capture is not None
                    else None
                )
                if cable_render is not None:
                    self._remember_windows_playback_default()
                    log = get_manager().switch_default_playback(
                        cable_render.name,
                        operation="NR ON -> VB-Cable",
                    )
                    if log is not None and log.changed:
                        result.windows_playback_hint = (
                            "Windows playback set to VB-Cable automatically."
                        )
                    else:
                        result.windows_playback_hint = (
                            "Could not switch Windows playback automatically. "
                            f"Set Windows playback to: {cable_render.name}"
                        )
            else:
                log = get_manager().switch_default_playback(
                    output.name,
                    operation="NR OFF -> Playback Output",
                )
                if log is not None and log.changed:
                    result.windows_playback_hint = (
                        f"Windows playback restored to {output.name}."
                    )
                else:
                    result.windows_playback_hint = (
                        "Could not switch Windows playback automatically. "
                        f"Set Windows playback to: {output.name}"
                    )

        if not self._platform.playback_running:
            cable_capture = self._playback_cable_capture()
            if cable_capture is None:
                result.playback_error = (
                    "VB-Cable is not available. Install VB-Audio Virtual Cable "
                    "to use playback processing."
                )
            else:
                self._platform.playback.input_device = cable_capture.index
                self._platform.playback.output_device = output.index
                try:
                    self._platform.start_playback()
                except Exception as exc:
                    result.playback_error = str(exc)

        self._persist_playback(output, nr_enabled, strength)
        return result

    def _update_microphone_chain(self, *, nr_enabled: bool, strength: float) -> None:
        chain = self._platform.microphone.chain
        chain.noise_reduction.enabled = nr_enabled
        chain.noise_reduction.strength = strength
        self._platform.sync_chain_slot_enabled(chain)

    def restart_microphone(
        self,
        microphone: DeviceEntry | None,
        virtual_output: DeviceEntry | None,
        *,
        nr_enabled: bool,
        strength: float,
    ) -> RoutingResult:
        """Restart the microphone pipeline when the input or output device changes."""
        result = RoutingResult()
        self._update_microphone_chain(nr_enabled=nr_enabled, strength=strength)
        self._platform.stop_microphone()

        if microphone is None or virtual_output is None:
            result.microphone_error = "Select a microphone and virtual output device."
            self._persist_microphone(microphone, virtual_output, nr_enabled, strength)
            return result

        self._platform.microphone.input_device = microphone.index
        self._platform.microphone.output_device = virtual_output.index
        try:
            if nr_enabled:
                NoiseReductionEffect.ensure_available()
            self._platform.start_microphone()
        except Exception as exc:
            result.microphone_error = str(exc)

        self._persist_microphone(microphone, virtual_output, nr_enabled, strength)
        return result

    def set_microphone_routing(
        self,
        microphone: DeviceEntry | None,
        virtual_output: DeviceEntry | None,
        *,
        nr_enabled: bool,
        strength: float,
        apply_windows: bool = True,
    ) -> RoutingResult:
        """Toggle NR bypass and Windows routing without restarting the pipeline."""
        result = RoutingResult()
        self._update_microphone_chain(nr_enabled=nr_enabled, strength=strength)

        if nr_enabled:
            try:
                NoiseReductionEffect.ensure_available()
            except ImportError as exc:
                result.microphone_error = str(exc)
                self._persist_microphone(microphone, virtual_output, nr_enabled, strength)
                return result

        if microphone is None or virtual_output is None:
            result.microphone_error = "Select a microphone and virtual output device."
            self._persist_microphone(microphone, virtual_output, nr_enabled, strength)
            return result

        if apply_windows and windows_defaults_supported():
            if nr_enabled and is_vb_cable_input_output(virtual_output):
                cable_capture = find_matching_cable_output(self._inputs, virtual_output)
                if cable_capture is not None:
                    self._remember_windows_recording_default()
                    log = get_manager().switch_default_recording(
                        cable_capture.name,
                        operation="NR ON -> VB-Cable recording",
                    )
                    if log is not None and log.changed:
                        result.windows_recording_hint = (
                            "Windows recording set to VB-Cable automatically."
                        )
                    else:
                        result.windows_recording_hint = (
                            "Could not switch Windows recording automatically. "
                            f"Set Windows recording to: {cable_capture.name}"
                        )
            else:
                restore_name = self._settings.saved_windows_recording or microphone.name
                log = get_manager().switch_default_recording(
                    restore_name,
                    operation="NR OFF -> Microphone",
                )
                if log is not None and log.changed:
                    result.windows_recording_hint = (
                        f"Windows recording restored to {restore_name}."
                    )
                else:
                    result.windows_recording_hint = (
                        "Could not switch Windows recording automatically. "
                        f"Set Windows recording to: {restore_name}"
                    )

        if not self._platform.microphone_running:
            self._platform.microphone.input_device = microphone.index
            self._platform.microphone.output_device = virtual_output.index
            try:
                self._platform.start_microphone()
            except Exception as exc:
                result.microphone_error = str(exc)

        self._persist_microphone(microphone, virtual_output, nr_enabled, strength)
        return result

    def apply_microphone(
        self,
        microphone: DeviceEntry | None,
        virtual_output: DeviceEntry | None,
        *,
        nr_enabled: bool,
        strength: float,
        apply_windows: bool = True,
    ) -> RoutingResult:
        """Backward-compatible entry point; restarts the microphone pipeline."""
        result = self.restart_microphone(
            microphone,
            virtual_output,
            nr_enabled=nr_enabled,
            strength=strength,
        )
        if apply_windows:
            windows_result = self.set_microphone_routing(
                microphone,
                virtual_output,
                nr_enabled=nr_enabled,
                strength=strength,
                apply_windows=True,
            )
            if windows_result.windows_recording_hint:
                result.windows_recording_hint = windows_result.windows_recording_hint
            if windows_result.microphone_error and not result.microphone_error:
                result.microphone_error = windows_result.microphone_error
        return result

    def update_playback_strength(self, strength: float) -> None:
        route = self._settings.playback_output or RouteSettings()
        route.noise_reduction_strength = strength
        self._settings.playback_output = route
        self._platform.playback.chain.noise_reduction.strength = strength
        save_settings(self._settings)

    def update_microphone_strength(self, strength: float) -> None:
        route_in = self._settings.microphone_input or RouteSettings()
        route_out = self._settings.microphone_output or RouteSettings()
        route_in.noise_reduction_strength = strength
        route_out.noise_reduction_strength = strength
        self._settings.microphone_input = route_in
        self._settings.microphone_output = route_out
        self._platform.microphone.chain.noise_reduction.strength = strength
        save_settings(self._settings)

    def _remember_windows_playback_default(self) -> None:
        if self._settings.saved_windows_playback is not None:
            return
        defaults = get_system_defaults()
        if defaults.playback_name:
            self._settings.saved_windows_playback = defaults.playback_name

    def _remember_windows_recording_default(self) -> None:
        if self._settings.saved_windows_recording is not None:
            return
        defaults = get_system_defaults()
        if defaults.recording_name:
            self._settings.saved_windows_recording = defaults.recording_name

    def _persist_playback(
        self,
        output: DeviceEntry | None,
        nr_enabled: bool,
        strength: float,
    ) -> None:
        if output is None:
            self._settings.playback_output = RouteSettings(
                noise_reduction_enabled=nr_enabled,
                noise_reduction_strength=strength,
            )
        else:
            self._settings.playback_output = RouteSettings(
                device_name=output.name,
                device_hostapi=output.hostapi,
                noise_reduction_enabled=nr_enabled,
                noise_reduction_strength=strength,
            )
        save_settings(self._settings)

    def _persist_microphone(
        self,
        microphone: DeviceEntry | None,
        virtual_output: DeviceEntry | None,
        nr_enabled: bool,
        strength: float,
    ) -> None:
        self._settings.microphone_input = RouteSettings(
            device_name=microphone.name if microphone else None,
            device_hostapi=microphone.hostapi if microphone else None,
            noise_reduction_enabled=nr_enabled,
            noise_reduction_strength=strength,
        )
        self._settings.microphone_output = RouteSettings(
            device_name=virtual_output.name if virtual_output else None,
            device_hostapi=virtual_output.hostapi if virtual_output else None,
            noise_reduction_enabled=nr_enabled,
            noise_reduction_strength=strength,
        )
        save_settings(self._settings)

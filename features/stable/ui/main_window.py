from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from audio.devices import DeviceEntry, list_usable_devices
from audio.device_utils import (
    filter_microphone_inputs,
    filter_playback_outputs,
    find_default_microphone,
    find_default_speakers,
    find_virtual_microphone_output,
    is_vb_cable_installed,
)
from audio.windows_device_restore import (
    capture_startup_defaults,
    capture_startup_recording_default,
    install_exit_restore,
)
from effects.noise_reduction import NoiseReductionEffect
from features import __version__
from features.stable.routing_controller import RoutingController
from features.stable.settings_store import load_settings, save_settings
from features.stable.ui.app_icon import (
    apply_application_icon,
    apply_window_icon,
    set_windows_app_user_model_id,
)
from features.stable.ui.activity_log import UiActivityLog, configure_ui_logging
from features.stable.ui.device_worker import DevicePollController
from features.stable.ui.route_panel import RoutePanel
from features.stable.ui.setup_dialog import VbCableSetupDialog
from features.stable.ui.theme import APP_STYLESHEET, apply_focus_stable_palette
from features.stable.ui.ui_icons import IconTextLabel
from pipeline.session import AudioPlatform

METRICS_INTERVAL_MS = 1000
DEVICE_POLL_INTERVAL_MS = 5000


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Clear Audio {__version__}")
        apply_window_icon(self)
        self.resize(720, 480)
        self.setMinimumSize(560, 420)

        self._platform = AudioPlatform()
        self._inputs = list_usable_devices("input")
        self._outputs = list_usable_devices("output")
        self._settings = load_settings()
        self._routing = RoutingController(
            self._platform,
            self._inputs,
            self._outputs,
            self._settings,
        )
        self._playback_error: str | None = None
        self._microphone_error: str | None = None
        self._last_playback_output: tuple[str, str] | None = None
        self._last_playback_nr: bool | None = None
        self._last_microphone_input: tuple[str, str] | None = None
        self._last_microphone_output: tuple[str, str] | None = None
        self._last_microphone_nr: bool | None = None
        self._activity = UiActivityLog()
        self._device_poll = DevicePollController()
        self._device_poll.set_baselines(self._inputs, self._outputs)
        self._device_poll.devices_refreshed.connect(self._on_devices_refreshed)
        self._device_poll.scan_failed.connect(self._on_device_scan_failed)

        self._build_ui()
        self._restore_user_selection()
        self._maybe_show_first_run_setup()
        saved_playback = (
            self._settings.playback_output is not None
            and self._settings.playback_output.device_name is not None
        )
        saved_microphone = (
            self._settings.microphone_input is not None
            and self._settings.microphone_input.device_name is not None
        )
        self._apply_playback_change(
            apply_windows=saved_playback,
            force_restart=True,
        )
        self._apply_microphone_change(
            apply_windows=saved_microphone,
            force_restart=True,
        )

        self._metrics_timer = QTimer(self)
        self._metrics_timer.setInterval(METRICS_INTERVAL_MS)
        self._metrics_timer.timeout.connect(self._update_status)
        self._metrics_timer.start()

        self._device_poll_timer = QTimer(self)
        self._device_poll_timer.setInterval(DEVICE_POLL_INTERVAL_MS)
        self._device_poll_timer.timeout.connect(self._device_poll.poll_fast)
        self._device_poll_timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)

        self.playback_panel = RoutePanel(
            title="What You Hear",
            title_icon="fa6s.headphones",
            platform=self._platform,
            chain_getter=lambda: self._platform.playback.chain,
            input_devices=self._inputs,
            output_devices=self._outputs,
            show_input=False,
            show_output=True,
            output_label="Listening Device",
            output_icon="fa6s.volume-high",
            filter_outputs=filter_playback_outputs,
        )
        self.playback_panel.config_changed.connect(self._on_playback_config_changed)
        self.playback_panel.nr_strength.valueChanged.connect(self._on_playback_strength_changed)
        root.addWidget(self.playback_panel)

        self.microphone_panel = RoutePanel(
            title="What You Send",
            title_icon="fa6s.headset",
            platform=self._platform,
            chain_getter=lambda: self._platform.microphone.chain,
            input_devices=self._inputs,
            output_devices=self._outputs,
            show_output=False,
            input_label="Microphone",
            input_icon="fa6s.microphone",
            filter_inputs=filter_microphone_inputs,
        )
        self.microphone_panel.config_changed.connect(self._on_microphone_config_changed)
        self.microphone_panel.nr_strength.valueChanged.connect(self._on_microphone_strength_changed)
        root.addWidget(self.microphone_panel)
        root.addStretch(1)

        status = self.statusBar()
        status.setSizeGripEnabled(False)

        self.playback_status = IconTextLabel("fa6s.headphones", "Listening: Inactive")
        self.microphone_status = IconTextLabel("fa6s.microphone", "Sending: Inactive")
        self.latency_status = IconTextLabel("fa6s.gauge-high", "Latency: —")

        status.addWidget(self.playback_status)
        status.addWidget(self._status_separator())
        status.addWidget(self.microphone_status)
        status.addWidget(self._status_separator())
        status.addWidget(self.latency_status)

    def _status_separator(self) -> QFrame:
        separator = QFrame()
        separator.setObjectName("statusSeparator")
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        return separator

    def _restore_user_selection(self) -> None:
        saved = self._settings

        playback = saved.playback_output
        if playback and playback.device_name:
            self.playback_panel.apply_selection(
                output_name=playback.device_name,
                output_hostapi=playback.device_hostapi,
                nr_enabled=playback.noise_reduction_enabled,
                nr_strength=playback.noise_reduction_strength,
            )
        else:
            speakers = find_default_speakers(self._outputs)
            for output in filter_playback_outputs(self._outputs):
                if speakers is not None and output.index == speakers:
                    self.playback_panel.apply_selection(
                        output_name=output.name,
                        output_hostapi=output.hostapi,
                        nr_enabled=False,
                    )
                    break

        mic_in = saved.microphone_input
        if mic_in and mic_in.device_name:
            self.microphone_panel.apply_selection(
                input_name=mic_in.device_name,
                input_hostapi=mic_in.device_hostapi,
                nr_enabled=mic_in.noise_reduction_enabled,
                nr_strength=mic_in.noise_reduction_strength,
            )
        else:
            mic_index = find_default_microphone(self._inputs)
            mic_entry = next(
                (
                    entry
                    for entry in filter_microphone_inputs(self._inputs)
                    if entry.index == mic_index
                ),
                None,
            )
            self.microphone_panel.apply_selection(
                input_name=mic_entry.name if mic_entry else None,
                input_hostapi=mic_entry.hostapi if mic_entry else None,
                nr_enabled=False,
            )

    def _maybe_show_first_run_setup(self) -> None:
        if self._settings.first_run_setup_completed:
            return
        if is_vb_cable_installed(self._inputs, self._outputs):
            self._settings.first_run_setup_completed = True
            save_settings(self._settings)
            return

        dialog = VbCableSetupDialog(self)
        dialog.exec()
        self._settings.first_run_setup_completed = True
        save_settings(self._settings)
        self._device_poll.refresh_full()

    def _on_playback_config_changed(self) -> None:
        self._apply_playback_change()

    def _playback_output_key(self) -> tuple[str, str] | None:
        output = self.playback_panel.selected_output_entry()
        if output is None:
            return None
        return (output.name, output.hostapi)

    def _apply_playback_change(
        self,
        *,
        apply_windows: bool = True,
        force_restart: bool = False,
    ) -> None:
        output = self.playback_panel.selected_output_entry()
        nr_enabled = self.playback_panel.noise_reduction_enabled()
        strength = self.playback_panel.noise_reduction_strength()
        output_key = self._playback_output_key()

        output_changed = force_restart or output_key != self._last_playback_output
        routing_changed = self._last_playback_nr is None or nr_enabled != self._last_playback_nr

        self._last_playback_output = output_key
        self._last_playback_nr = nr_enabled

        if output_changed:
            result = self._routing.restart_playback(
                output,
                nr_enabled=nr_enabled,
                strength=strength,
            )
            if apply_windows:
                windows_result = self._routing.set_playback_routing(
                    output,
                    nr_enabled=nr_enabled,
                    strength=strength,
                    apply_windows=True,
                )
                result.windows_playback_hint = windows_result.windows_playback_hint
                if windows_result.playback_error and not result.playback_error:
                    result.playback_error = windows_result.playback_error
        elif routing_changed:
            result = self._routing.set_playback_routing(
                output,
                nr_enabled=nr_enabled,
                strength=strength,
                apply_windows=apply_windows,
            )
        else:
            return

        self._playback_error = result.playback_error
        self._update_status()

    def _on_microphone_config_changed(self) -> None:
        self._apply_microphone_change()

    def _auto_virtual_output(self) -> DeviceEntry | None:
        return find_virtual_microphone_output(self._outputs)

    def _microphone_device_keys(
        self,
    ) -> tuple[tuple[str, str] | None, tuple[str, str] | None]:
        microphone = self.microphone_panel.selected_input_entry()
        virtual_output = self._auto_virtual_output()
        mic_key = (microphone.name, microphone.hostapi) if microphone else None
        out_key = (
            (virtual_output.name, virtual_output.hostapi) if virtual_output else None
        )
        return mic_key, out_key

    def _apply_microphone_change(
        self,
        *,
        apply_windows: bool = True,
        force_restart: bool = False,
    ) -> None:
        microphone = self.microphone_panel.selected_input_entry()
        virtual_output = self._auto_virtual_output()
        nr_enabled = self.microphone_panel.noise_reduction_enabled()
        strength = self.microphone_panel.noise_reduction_strength()
        mic_key, out_key = self._microphone_device_keys()

        devices_changed = (
            force_restart
            or mic_key != self._last_microphone_input
            or out_key != self._last_microphone_output
        )
        routing_changed = (
            self._last_microphone_nr is None or nr_enabled != self._last_microphone_nr
        )

        self._last_microphone_input = mic_key
        self._last_microphone_output = out_key
        self._last_microphone_nr = nr_enabled

        if devices_changed:
            result = self._routing.restart_microphone(
                microphone,
                virtual_output,
                nr_enabled=nr_enabled,
                strength=strength,
            )
            if apply_windows:
                windows_result = self._routing.set_microphone_routing(
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
        elif routing_changed:
            result = self._routing.set_microphone_routing(
                microphone,
                virtual_output,
                nr_enabled=nr_enabled,
                strength=strength,
                apply_windows=apply_windows,
            )
        else:
            return

        self._microphone_error = result.microphone_error
        self._update_status()

    def _on_playback_strength_changed(self, _value: int) -> None:
        self._routing.update_playback_strength(
            self.playback_panel.noise_reduction_strength()
        )

    def _on_microphone_strength_changed(self, _value: int) -> None:
        self._routing.update_microphone_strength(
            self.microphone_panel.noise_reduction_strength()
        )

    def _apply_playback_routing(self, *, apply_windows: bool = True) -> None:
        self._apply_playback_change(apply_windows=apply_windows)

    def _apply_microphone_routing(self, *, apply_windows: bool = True) -> None:
        self._apply_microphone_change(apply_windows=apply_windows)

    def _on_device_scan_failed(self, _message: str) -> None:
        return

    def _on_devices_refreshed(
        self,
        new_inputs: list[DeviceEntry],
        new_outputs: list[DeviceEntry],
    ) -> None:
        self._inputs = new_inputs
        self._outputs = new_outputs
        self._routing.update_device_lists(new_inputs, new_outputs)
        self._device_poll.set_baselines(new_inputs, new_outputs)

        self.playback_panel.refresh_devices(new_inputs, new_outputs)
        self.microphone_panel.refresh_devices(new_inputs, new_outputs)

        self._activity.record_device_refresh(manual=False)

        self._apply_playback_change(force_restart=True)
        self._apply_microphone_change(force_restart=True)

    def _route_label(self, name: str, running: bool, error: str | None) -> str:
        if error:
            return f"{name}: Error"
        if running:
            return f"{name}: Active"
        return f"{name}: Inactive"

    def _update_status(self) -> None:
        self._activity.record_status_update()

        pb = self._platform.playback_metrics()
        mic = self._platform.microphone_metrics()

        pb_running = pb is not None and pb.is_running
        mic_running = mic is not None and mic.is_running

        playback_text = self._route_label("Listening", pb_running, self._playback_error)
        microphone_text = self._route_label("Sending", mic_running, self._microphone_error)
        if playback_text != self.playback_status.text():
            self.playback_status.setText(playback_text)
        if microphone_text != self.microphone_status.text():
            self.microphone_status.setText(microphone_text)

        latencies: list[float] = []
        if pb_running and pb is not None:
            latencies.append(pb.latency_ms)
        if mic_running and mic is not None:
            latencies.append(mic.latency_ms)

        latency_text = (
            f"Latency: {max(latencies):.0f} ms" if latencies else "Latency: —"
        )
        if latency_text != self.latency_status.text():
            self.latency_status.setText(latency_text)

    def closeEvent(self, event: Any) -> None:
        self._platform.stop_all()
        super().closeEvent(event)


def run() -> None:
    configure_ui_logging()
    set_windows_app_user_model_id()
    app = QApplication(sys.argv)
    apply_application_icon(app)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    apply_focus_stable_palette(app)
    capture_startup_defaults()
    capture_startup_recording_default()
    install_exit_restore(app)
    try:
        NoiseReductionEffect.ensure_available()
    except ImportError as exc:
        QMessageBox.warning(
            None,
            "Clear Audio",
            f"Noise Reduction is not available on this system.\n\n{exc}\n\n"
            "Please use Python 3.10–3.12.",
        )
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

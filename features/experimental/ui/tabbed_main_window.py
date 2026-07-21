"""Experimental tabbed UI (v2 development)."""

from __future__ import annotations

import sys
from typing import Any

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from audio.devices import list_usable_devices
from effects.noise_reduction import NoiseReductionEffect
from features.experimental.ui.microphone_tab import MicrophoneTab
from features.experimental.ui.playback_tab import PlaybackTab
from features.experimental.ui.plugins_tab import PluginsTab
from features.experimental.config import default_microphone_chain, default_playback_chain
from pipeline.session import AudioPlatform


class TabbedMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clear Audio – Experimental (v2)")
        self.resize(780, 680)

        self._platform = AudioPlatform()
        self._platform.playback.chain = default_playback_chain()
        self._platform.microphone.chain = default_microphone_chain()
        self._inputs = list_usable_devices("input")
        self._outputs = list_usable_devices("output")

        self._build_ui()

        self._metrics_timer = QTimer(self)
        self._metrics_timer.setInterval(500)
        self._metrics_timer.timeout.connect(self._update_metrics)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.playback_tab = PlaybackTab(self._platform, self._inputs, self._outputs)
        self.microphone_tab = MicrophoneTab(self._platform, self._inputs, self._outputs)
        self.plugins_tab = PluginsTab(self._platform)
        self.plugins_tab.plugins_changed.connect(self._on_plugins_changed)
        self.tabs.addTab(self.playback_tab, "Playback")
        self.tabs.addTab(self.microphone_tab, "Mikrofon")
        self.tabs.addTab(self.plugins_tab, "Plugins")
        layout.addWidget(self.tabs)

        status = QGroupBox("Status")
        status_form = QFormLayout(status)
        self.cpu_label = QLabel("–")
        self.playback_status = QLabel("Gestoppt")
        self.microphone_status = QLabel("Gestoppt")
        self.playback_latency = QLabel("–")
        self.microphone_latency = QLabel("–")
        status_form.addRow("CPU:", self.cpu_label)
        status_form.addRow("Playback:", self.playback_status)
        status_form.addRow("Playback-Latenz:", self.playback_latency)
        status_form.addRow("Mikrofon:", self.microphone_status)
        status_form.addRow("Mikrofon-Latenz:", self.microphone_latency)
        layout.addWidget(status)

    def _on_plugins_changed(self) -> None:
        self.playback_tab.refresh_effects()
        self.microphone_tab.refresh_effects()

    def _update_metrics(self) -> None:
        self.cpu_label.setText(f"{psutil.cpu_percent(interval=None):.1f} %")

        pb = self._platform.playback_metrics()
        if pb and pb.is_running:
            self.playback_status.setText("Läuft")
            self.playback_latency.setText(
                f"{pb.latency_ms:.1f} ms ({pb.process_ms:.1f} ms/Block)"
            )
            self.playback_tab.set_running_state(True)
        else:
            self.playback_status.setText("Gestoppt")
            self.playback_latency.setText("–")
            self.playback_tab.set_running_state(False)

        mic = self._platform.microphone_metrics()
        if mic and mic.is_running:
            self.microphone_status.setText("Läuft")
            self.microphone_latency.setText(
                f"{mic.latency_ms:.1f} ms ({mic.process_ms:.1f} ms/Block)"
            )
            self.microphone_tab.set_running_state(True)
        else:
            self.microphone_status.setText("Gestoppt")
            self.microphone_latency.setText("–")
            self.microphone_tab.set_running_state(False)

        if (pb and pb.is_running) or (mic and mic.is_running):
            if not self._metrics_timer.isActive():
                self._metrics_timer.start()
        else:
            self._metrics_timer.stop()

    def closeEvent(self, event: Any) -> None:
        self._platform.stop_all()
        super().closeEvent(event)


def run() -> None:
    app = QApplication(sys.argv)
    try:
        NoiseReductionEffect.ensure_available()
    except ImportError as exc:
        QMessageBox.warning(
            None,
            "DeepFilterNet",
            f"{exc}\n\nNoise Reduction benötigt Python 3.10–3.12.",
        )
    window = TabbedMainWindow()
    window.show()
    sys.exit(app.exec())

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from audio.devices import DeviceEntry, format_device_label
from features.experimental.ui.effect_chain_rack import EffectChainRack
from pipeline.session import AudioPlatform
from audio.device_utils import (
    find_default_speakers,
    find_default_vb_cable_output,
)


class PlaybackTab(QWidget):
    def __init__(
        self, platform: AudioPlatform, inputs: list[DeviceEntry], outputs: list[DeviceEntry]
    ) -> None:
        super().__init__()
        self._platform = platform
        self._inputs = inputs
        self._outputs = outputs
        self._build_ui()
        self._apply_defaults()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        devices = QGroupBox("Playback-Routing")
        form = QFormLayout(devices)
        self.input_combo = QComboBox()
        for entry in self._inputs:
            self.input_combo.addItem(format_device_label(entry), entry.index)
        self.output_combo = QComboBox()
        for entry in self._outputs:
            self.output_combo.addItem(format_device_label(entry), entry.index)
        form.addRow("Eingang (VB-Cable):", self.input_combo)
        form.addRow("Ausgang (Lautsprecher):", self.output_combo)
        layout.addWidget(devices)

        self.effect_rack = EffectChainRack(
            platform=self._platform,
            chain_getter=lambda: self._platform.playback.chain,
            route="playback",
            title="Effektkette Playback",
        )
        layout.addWidget(self.effect_rack)

        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Playback starten")
        self.stop_btn = QPushButton("Playback stoppen")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.stop_btn)
        layout.addLayout(buttons)

        hint = QLabel(
            "Windows-Ausgabe auf „CABLE Input“ routen, dann „CABLE Output“ als Eingang wählen."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        layout.addStretch()

    def refresh_effects(self) -> None:
        self.effect_rack.refresh()

    def _apply_defaults(self) -> None:
        default_in = find_default_vb_cable_output(self._inputs)
        if default_in is not None:
            index = self.input_combo.findData(default_in)
            if index >= 0:
                self.input_combo.setCurrentIndex(index)
        default_out = find_default_speakers(self._outputs)
        if default_out is not None:
            index = self.output_combo.findData(default_out)
            if index >= 0:
                self.output_combo.setCurrentIndex(index)

    def _start(self) -> None:
        self._platform.playback.input_device = self.input_combo.currentData()
        self._platform.playback.output_device = self.output_combo.currentData()
        self._platform.sync_chain_slot_enabled(self._platform.playback.chain)
        try:
            self._platform.start_playback()
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Playback fehlgeschlagen", str(exc))
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.input_combo.setEnabled(False)
        self.output_combo.setEnabled(False)

    def _stop(self) -> None:
        self._platform.stop_playback()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.input_combo.setEnabled(True)
        self.output_combo.setEnabled(True)

    def set_running_state(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.input_combo.setEnabled(not running)
        self.output_combo.setEnabled(not running)
        self.effect_rack.set_chain_controls_enabled(not running)

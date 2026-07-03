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
from audio.device_utils import find_default_cable_input, find_default_microphone


class MicrophoneTab(QWidget):
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

        devices = QGroupBox("Mikrofon-Routing")
        form = QFormLayout(devices)
        self.input_combo = QComboBox()
        for entry in self._inputs:
            if "cable" in entry.name.lower():
                continue
            self.input_combo.addItem(format_device_label(entry), entry.index)
        if self.input_combo.count() == 0:
            for entry in self._inputs:
                self.input_combo.addItem(format_device_label(entry), entry.index)

        self.output_combo = QComboBox()
        for entry in self._outputs:
            self.output_combo.addItem(format_device_label(entry), entry.index)

        form.addRow("Mikrofon:", self.input_combo)
        form.addRow("Virtueller Ausgang:", self.output_combo)
        layout.addWidget(devices)

        self.effect_rack = EffectChainRack(
            platform=self._platform,
            chain_getter=lambda: self._platform.microphone.chain,
            route="microphone",
            title="Effektkette Mikrofon",
        )
        layout.addWidget(self.effect_rack)

        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Mikrofon starten")
        self.stop_btn = QPushButton("Mikrofon stoppen")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.stop_btn)
        layout.addLayout(buttons)

        hint = QLabel(
            "Virtuellen Ausgang auf „CABLE Input“ setzen, um das bearbeitete Mikrofon "
            "in anderen Anwendungen zu nutzen."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        layout.addStretch()

    def refresh_effects(self) -> None:
        self.effect_rack.refresh()

    def _apply_defaults(self) -> None:
        mic = find_default_microphone(self._inputs)
        if mic is not None:
            index = self.input_combo.findData(mic)
            if index >= 0:
                self.input_combo.setCurrentIndex(index)
        cable = find_default_cable_input(self._outputs)
        if cable is not None:
            index = self.output_combo.findData(cable)
            if index >= 0:
                self.output_combo.setCurrentIndex(index)

    def _start(self) -> None:
        self._platform.microphone.input_device = self.input_combo.currentData()
        self._platform.microphone.output_device = self.output_combo.currentData()
        self._platform.sync_chain_slot_enabled(self._platform.microphone.chain)
        try:
            self._platform.start_microphone()
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Mikrofon fehlgeschlagen", str(exc))
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.input_combo.setEnabled(False)
        self.output_combo.setEnabled(False)

    def _stop(self) -> None:
        self._platform.stop_microphone()
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

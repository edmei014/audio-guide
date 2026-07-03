from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from effects.equalizer import EQ_PRESETS
from pipeline.effect_chain import ChainSlot, EffectChainConfig
from pipeline.session import AudioPlatform

RouteName = Literal["playback", "microphone"]


class EffectChainRack(QGroupBox):
    """Self-contained effect rack: chain list, controls, and inline parameters."""

    def __init__(
        self,
        platform: AudioPlatform,
        chain_getter: Callable[[], EffectChainConfig],
        route: RouteName,
        title: str,
    ) -> None:
        super().__init__(title)
        self._platform = platform
        self._chain_getter = chain_getter
        self._route = route
        self._parameter_widgets: dict[str, QDoubleSpinBox] = {}
        self._updating_parameters = False
        self._selected_slot_id: str | None = None
        self._build_ui()
        self.refresh()

    def _chain(self) -> EffectChainConfig:
        return self._chain_getter()

    def _is_running(self) -> bool:
        if self._route == "playback":
            return self._platform.playback_running
        return self._platform.microphone_running

    def _vst_names(self) -> dict[str, str]:
        return {plugin.instance_id: plugin.name for plugin in self._platform.vst_host.plugins}

    def _slot_label(self, index: int, slot: ChainSlot) -> str:
        names = self._vst_names()
        if slot.kind == "builtin":
            name = slot.effect_type.replace("_", " ").title()
        else:
            name = names.get(slot.effect_type, "VST3 Plugin")
        state = "aktiv" if slot.enabled else "inaktiv"
        return f"{index + 1}. {name}  [{state}]"

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.chain_list = QListWidget()
        self.chain_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.chain_list)

        controls = QHBoxLayout()
        self.up_btn = QPushButton("Nach oben")
        self.down_btn = QPushButton("Nach unten")
        self.toggle_btn = QPushButton("Aktivieren/Deaktivieren")
        self.remove_btn = QPushButton("Entfernen")
        self.up_btn.clicked.connect(lambda: self._move_selected(-1))
        self.down_btn.clicked.connect(lambda: self._move_selected(1))
        self.toggle_btn.clicked.connect(self._toggle_selected)
        self.remove_btn.clicked.connect(self._remove_selected)
        controls.addWidget(self.up_btn)
        controls.addWidget(self.down_btn)
        controls.addWidget(self.toggle_btn)
        controls.addWidget(self.remove_btn)
        layout.addLayout(controls)

        self.param_placeholder = QLabel("Effekt auswählen, um Parameter zu bearbeiten.")
        self.param_placeholder.setStyleSheet("color: #666;")
        layout.addWidget(self.param_placeholder)

        self.param_scroll = QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_scroll.setVisible(False)
        self.param_container = QWidget()
        self.param_form = QFormLayout(self.param_container)
        self.param_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.param_scroll.setWidget(self.param_container)
        layout.addWidget(self.param_scroll)

        add_row = QHBoxLayout()
        self.add_vst_combo = QComboBox()
        self.add_vst_combo.setPlaceholderText("Geladenes Plugin wählen…")
        self.add_vst_btn = QPushButton("Plugin zur Kette hinzufügen")
        self.add_vst_btn.clicked.connect(self._add_vst_to_chain)
        add_row.addWidget(self.add_vst_combo, stretch=1)
        add_row.addWidget(self.add_vst_btn)
        layout.addLayout(add_row)

        hint = QLabel(
            "VST-Plugins zuerst im Tab „Plugins“ laden. "
            "Kettenänderungen bei laufender Pipeline erfordern Neustart."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)

    def refresh(self) -> None:
        self._refresh_chain_list()
        self._refresh_add_vst_combo()
        if self._selected_slot_id is not None:
            self._populate_parameters(self._selected_slot_id)

    def _refresh_add_vst_combo(self) -> None:
        current = self.add_vst_combo.currentData()
        self.add_vst_combo.clear()
        for plugin in self._platform.vst_host.plugins:
            if not plugin.loaded:
                continue
            self.add_vst_combo.addItem(plugin.name, plugin.instance_id)
        if current is not None:
            index = self.add_vst_combo.findData(current)
            if index >= 0:
                self.add_vst_combo.setCurrentIndex(index)

    def _refresh_chain_list(self) -> None:
        selected = self._selected_slot_id
        self.chain_list.clear()
        chain = self._chain()
        for index, slot in enumerate(chain.slots):
            item = QListWidgetItem(self._slot_label(index, slot))
            item.setData(Qt.ItemDataRole.UserRole, slot.slot_id)
            self.chain_list.addItem(item)
            if slot.slot_id == selected:
                self.chain_list.setCurrentItem(item)

        if self.chain_list.currentItem() is None and self.chain_list.count() > 0:
            self.chain_list.setCurrentRow(0)

    def _selected_slot(self) -> ChainSlot | None:
        item = self.chain_list.currentItem()
        if item is None:
            return None
        slot_id = item.data(Qt.ItemDataRole.UserRole)
        return next((slot for slot in self._chain().slots if slot.slot_id == slot_id), None)

    def _on_selection_changed(self) -> None:
        slot = self._selected_slot()
        if slot is None:
            self._selected_slot_id = None
            self._clear_parameter_panel()
            return
        self._selected_slot_id = slot.slot_id
        self._populate_parameters(slot.slot_id)

    def _clear_parameter_panel(self) -> None:
        self._parameter_widgets.clear()
        while self.param_form.rowCount() > 0:
            self.param_form.removeRow(0)
        self.param_scroll.setVisible(False)
        self.param_placeholder.setVisible(True)

    def _populate_parameters(self, slot_id: str) -> None:
        self._clear_parameter_panel()
        chain = self._chain()
        slot = next((s for s in chain.slots if s.slot_id == slot_id), None)
        if slot is None:
            return

        if slot.kind == "builtin" and slot.effect_type == "noise_reduction":
            self._build_noise_reduction_params(chain)
        elif slot.kind == "builtin" and slot.effect_type == "equalizer":
            self._build_equalizer_params(chain)
        elif slot.kind == "vst":
            self._build_vst_params(slot.effect_type)
        else:
            self.param_placeholder.setText("Keine Parameter für diesen Effekt.")
            self.param_placeholder.setVisible(True)
            return

        self.param_placeholder.setVisible(False)
        self.param_scroll.setVisible(True)

    def _build_noise_reduction_params(self, chain: EffectChainConfig) -> None:
        settings = chain.noise_reduction

        strength = QSlider(Qt.Orientation.Horizontal)
        strength.setRange(0, 100)
        strength.setValue(int(settings.strength * 100))
        strength_label = QLabel(f"{strength.value()} %")

        def on_strength(value: int) -> None:
            strength_label.setText(f"{value} %")
            settings.strength = value / 100.0

        strength.valueChanged.connect(on_strength)

        strength_row = QHBoxLayout()
        strength_row.addWidget(strength)
        strength_row.addWidget(strength_label)
        strength_widget = QWidget()
        strength_widget.setLayout(strength_row)
        self.param_form.addRow("Stärke:", strength_widget)

        atten = QDoubleSpinBox()
        atten.setRange(0.0, 100.0)
        atten.setValue(settings.atten_lim)
        atten.setSuffix(" dB")
        atten.valueChanged.connect(lambda value: setattr(settings, "atten_lim", value))
        self.param_form.addRow("Max. Dämpfung:", atten)

    def _build_equalizer_params(self, chain: EffectChainConfig) -> None:
        settings = chain.equalizer
        preset = QComboBox()
        preset.addItems(list(EQ_PRESETS.keys()))
        preset.setCurrentText(settings.preset)
        preset.currentTextChanged.connect(settings.apply_preset)
        self.param_form.addRow("Preset:", preset)

    def _build_vst_params(self, instance_id: str) -> None:
        parameters = self._platform.vst_host.get_parameters(instance_id)
        if not parameters:
            self.param_placeholder.setText("Keine Parameter verfügbar.")
            self.param_placeholder.setVisible(True)
            self.param_scroll.setVisible(False)
            return

        self._updating_parameters = True
        for param in parameters:
            spin = QDoubleSpinBox()
            spin.setDecimals(4)
            spin.setMinimum(param.minimum)
            spin.setMaximum(param.maximum)
            spin.setValue(param.value)
            if param.units:
                spin.setSuffix(f" {param.units}")
            spin.setToolTip(param.name)
            spin.valueChanged.connect(
                lambda value, name=param.name, pid=instance_id: self._on_vst_parameter_changed(
                    pid, name, value
                )
            )
            label = param.label or param.name
            self.param_form.addRow(label, spin)
            self._parameter_widgets[param.name] = spin
        self._updating_parameters = False

    def _on_vst_parameter_changed(self, instance_id: str, name: str, value: float) -> None:
        if self._updating_parameters:
            return
        try:
            self._platform.vst_host.set_parameter(instance_id, name, value)
        except (KeyError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Parameter", str(exc))

    def _move_selected(self, direction: int) -> None:
        slot = self._selected_slot()
        if slot is None:
            return
        if self._is_running():
            QMessageBox.information(
                self,
                "Kette gesperrt",
                "Reihenfolge kann während aktiver Pipeline nicht geändert werden.",
            )
            return
        self._chain().move_slot(slot.slot_id, direction)
        self.refresh()

    def _toggle_selected(self) -> None:
        slot = self._selected_slot()
        if slot is None:
            return
        chain = self._chain()
        slot.enabled = not slot.enabled
        if slot.kind == "builtin" and slot.effect_type == "noise_reduction":
            chain.noise_reduction.enabled = slot.enabled
        elif slot.kind == "builtin" and slot.effect_type == "equalizer":
            chain.equalizer.enabled = slot.enabled
        elif slot.kind == "vst":
            self._platform.vst_host.set_enabled(slot.effect_type, slot.enabled)
        self.refresh()

    def _remove_selected(self) -> None:
        slot = self._selected_slot()
        if slot is None:
            return
        if slot.kind == "builtin":
            QMessageBox.information(
                self,
                "Geschützt",
                "Built-in-Effekte können nicht entfernt, nur deaktiviert werden.",
            )
            return
        if self._is_running():
            QMessageBox.information(
                self,
                "Kette gesperrt",
                "Effekte können während aktiver Pipeline nicht entfernt werden.",
            )
            return
        self._chain().remove_slot(slot.slot_id)
        self._selected_slot_id = None
        self.refresh()

    def _add_vst_to_chain(self) -> None:
        instance_id = self.add_vst_combo.currentData()
        if instance_id is None:
            QMessageBox.warning(
                self,
                "Kein Plugin",
                "Bitte zuerst im Tab „Plugins“ ein VST3-Plugin laden.",
            )
            return

        chain = self._chain()
        plugin = self._platform.vst_host.get_plugin(instance_id)
        plugin_name = plugin.name if plugin else str(instance_id)

        if any(s.kind == "vst" and s.effect_type == instance_id for s in chain.slots):
            QMessageBox.information(
                self,
                "Bereits in Kette",
                f"„{plugin_name}“ ist bereits in dieser Kette.",
            )
            return

        slot = chain.add_vst(instance_id)
        self._selected_slot_id = slot.slot_id
        self.refresh()

        if self._is_running():
            route_label = "Playback" if self._route == "playback" else "Mikrofon"
            QMessageBox.information(
                self,
                "Zur Kette hinzugefügt",
                f"„{plugin_name}“ wurde zur {route_label}-Kette hinzugefügt.\n\n"
                "Pipeline neu starten, damit das Plugin aktiv wird.",
            )

    def set_chain_controls_enabled(self, enabled: bool) -> None:
        """Disable structural edits while pipeline is running (parameters stay editable)."""
        self.up_btn.setEnabled(enabled)
        self.down_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled)
        self.add_vst_btn.setEnabled(enabled)

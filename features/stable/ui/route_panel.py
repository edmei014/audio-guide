from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from audio.devices import DeviceEntry
from features.stable.ui.strength_slider import StrengthSlider
from features.stable.ui.toggle_switch import ToggleSwitch
from features.stable.ui.ui_icons import (
    COLOR_LABEL,
    COLOR_TITLE,
    FORM_LABEL_COLUMN_WIDTH,
    ICON_SPACING,
    icon_column_spacer,
    icon_label,
    labeled_text_widget,
)
from pipeline.effect_chain import EffectChainConfig
from pipeline.session import AudioPlatform


def _device_label(entry: DeviceEntry) -> str:
    return f"{entry.name} — {entry.hostapi}"


class RoutePanel(QWidget):
    """Device and noise-reduction controls; changes apply immediately."""

    config_changed = Signal()

    def __init__(
        self,
        title: str,
        platform: AudioPlatform,
        chain_getter: Callable[[], EffectChainConfig],
        input_devices: list[DeviceEntry],
        output_devices: list[DeviceEntry],
        *,
        show_input: bool = True,
        show_output: bool = True,
        input_label: str = "Input",
        output_label: str = "Output",
        title_icon: str | None = None,
        input_icon: str | None = None,
        output_icon: str | None = None,
        filter_inputs: Callable[[list[DeviceEntry]], list[DeviceEntry]] | None = None,
        filter_outputs: Callable[[list[DeviceEntry]], list[DeviceEntry]] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("routeCard")
        self._platform = platform
        self._chain_getter = chain_getter
        self._block_changes = False
        self._show_input = show_input
        self._show_output = show_output
        self._input_label_text = input_label
        self._output_label_text = output_label
        self._title_icon = title_icon
        self._input_icon = input_icon
        self._output_icon = output_icon
        self._filter_inputs = filter_inputs
        self._filter_outputs = filter_outputs
        self._input_devices = list(input_devices)
        self._output_devices = list(output_devices)
        self._title = title
        self._build_ui()
        self._populate_device_combos()
        self._update_strength_interaction_lock()

    def _chain(self) -> EffectChainConfig:
        return self._chain_getter()

    def _filtered_inputs(self) -> list[DeviceEntry]:
        filtered = (
            self._filter_inputs(self._input_devices)
            if self._filter_inputs
            else self._input_devices
        )
        return filtered or self._input_devices

    def _filtered_outputs(self) -> list[DeviceEntry]:
        filtered = (
            self._filter_outputs(self._output_devices)
            if self._filter_outputs
            else self._output_devices
        )
        return filtered or self._output_devices

    @staticmethod
    def _form_label(text: str, icon_name: str | None = None) -> QWidget:
        row = QWidget()
        row.setFixedWidth(FORM_LABEL_COLUMN_WIDTH)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(ICON_SPACING)
        if icon_name:
            layout.addWidget(icon_label(icon_name, COLOR_LABEL))
        else:
            layout.addWidget(icon_column_spacer())
        label = QLabel(text)
        label.setObjectName("routeFieldLabel")
        layout.addWidget(label)
        layout.addStretch()
        return row

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        if self._title_icon:
            root.addWidget(
                labeled_text_widget(
                    self._title,
                    self._title_icon,
                    color=COLOR_TITLE,
                    object_name="routeCardTitle",
                )
            )
        else:
            title_label = QLabel(self._title)
            title_label.setObjectName("routeCardTitle")
            root.addWidget(title_label)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(20)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        chain = self._chain()

        self.input_combo = QComboBox()
        self.input_combo.currentIndexChanged.connect(self._notify_config_changed)

        self.output_combo = QComboBox()
        self.output_combo.currentIndexChanged.connect(self._notify_config_changed)

        if self._show_input:
            form.addRow(
                self._form_label(self._input_label_text, self._input_icon),
                self.input_combo,
            )

        if self._show_output:
            form.addRow(
                self._form_label(self._output_label_text, self._output_icon),
                self.output_combo,
            )

        self.nr_enable = ToggleSwitch("")
        self.nr_enable.setChecked(chain.noise_reduction.enabled)
        self.nr_enable.toggled.connect(self._on_nr_enable)
        form.addRow(
            self._form_label("Enable Noise Reduction", "fa6s.wave-square"),
            self.nr_enable,
        )

        self.nr_strength = StrengthSlider(Qt.Orientation.Horizontal)
        self.nr_strength.setObjectName("strengthSlider")
        self.nr_strength.setRange(0, 100)
        self.nr_strength.setValue(int(chain.noise_reduction.strength * 100))
        self.nr_strength.valueChanged.connect(self._on_nr_strength)
        self.nr_strength_label = QLabel(self._strength_text(self.nr_strength.value()))
        self.nr_strength_label.setObjectName("strengthValue")
        self.nr_strength_label.setMinimumWidth(44)
        self.nr_strength_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        strength_row = QHBoxLayout()
        strength_row.setContentsMargins(0, 0, 0, 0)
        strength_row.setSpacing(10)
        strength_row.addWidget(self.nr_strength, stretch=1)
        strength_row.addWidget(self.nr_strength_label)

        strength_host = QWidget()
        strength_host.setLayout(strength_row)
        form.addRow(self._form_label("Strength", "fa6s.sliders"), strength_host)

        root.addLayout(form)

    @staticmethod
    def _strength_text(value: int) -> str:
        return f"{value}%"

    def _populate_device_combos(self) -> None:
        self._block_changes = True
        if self._show_input:
            input_index = self.selected_input_device()
            self.input_combo.clear()
            for entry in self._filtered_inputs():
                self.input_combo.addItem(_device_label(entry), entry.index)
            if input_index is not None:
                combo_index = self.input_combo.findData(input_index)
                if combo_index >= 0:
                    self.input_combo.setCurrentIndex(combo_index)

        output_index = self.selected_output_device()
        if self._show_output:
            self.output_combo.clear()
            for entry in self._filtered_outputs():
                self.output_combo.addItem(_device_label(entry), entry.index)
            if output_index is not None:
                combo_index = self.output_combo.findData(output_index)
                if combo_index >= 0:
                    self.output_combo.setCurrentIndex(combo_index)
        self._block_changes = False

    def _notify_config_changed(self) -> None:
        if self._block_changes:
            return
        self.config_changed.emit()

    def _on_nr_enable(self, enabled: bool) -> None:
        self._update_strength_interaction_lock()
        chain = self._chain()
        chain.noise_reduction.enabled = enabled
        self._platform.sync_chain_slot_enabled(chain)
        self._notify_config_changed()

    def _update_strength_interaction_lock(self) -> None:
        self.nr_strength.set_interaction_locked(not self.nr_enable.isChecked())

    def _on_nr_strength(self, value: int) -> None:
        self.nr_strength_label.setText(self._strength_text(value))
        self._chain().noise_reduction.strength = value / 100.0

    def selected_input_device(self) -> int | None:
        if not self._show_input:
            return None
        return self.input_combo.currentData()

    def selected_output_device(self) -> int | None:
        if not self._show_output:
            return None
        return self.output_combo.currentData()

    def selected_input_entry(self) -> DeviceEntry | None:
        index = self.selected_input_device()
        if index is None:
            return None
        for entry in self._filtered_inputs():
            if entry.index == index:
                return entry
        return None

    def selected_output_entry(self) -> DeviceEntry | None:
        if not self._show_output:
            return None
        index = self.selected_output_device()
        if index is None:
            return None
        for entry in self._filtered_outputs():
            if entry.index == index:
                return entry
        return None

    def noise_reduction_enabled(self) -> bool:
        return self.nr_enable.isChecked()

    def noise_reduction_strength(self) -> float:
        return self.nr_strength.value() / 100.0

    def apply_selection(
        self,
        *,
        input_name: str | None = None,
        input_hostapi: str | None = None,
        output_name: str | None = None,
        output_hostapi: str | None = None,
        nr_enabled: bool | None = None,
        nr_strength: float | None = None,
    ) -> None:
        self._block_changes = True
        if self._show_input and input_name is not None:
            for entry in self._filtered_inputs():
                if entry.name == input_name and (
                    input_hostapi is None or entry.hostapi == input_hostapi
                ):
                    index = self.input_combo.findData(entry.index)
                    if index >= 0:
                        self.input_combo.setCurrentIndex(index)
                    break
        if output_name is not None and self._show_output:
            for entry in self._filtered_outputs():
                if entry.name == output_name and (
                    output_hostapi is None or entry.hostapi == output_hostapi
                ):
                    index = self.output_combo.findData(entry.index)
                    if index >= 0:
                        self.output_combo.setCurrentIndex(index)
                    break
        if nr_enabled is not None:
            self.nr_enable.setChecked(nr_enabled)
        if nr_strength is not None:
            self.nr_strength.setValue(int(nr_strength * 100))
            self.nr_strength_label.setText(self._strength_text(self.nr_strength.value()))
        self._block_changes = False
        self._update_strength_interaction_lock()

    def refresh_devices(
        self,
        input_devices: list[DeviceEntry],
        output_devices: list[DeviceEntry],
    ) -> None:
        preserved_input = self.selected_input_entry()
        preserved_output = self.selected_output_entry()
        self._input_devices = list(input_devices)
        self._output_devices = list(output_devices)
        self._populate_device_combos()

        if preserved_input is not None:
            self.apply_selection(
                input_name=preserved_input.name,
                input_hostapi=preserved_input.hostapi,
            )
        if preserved_output is not None and self._show_output:
            self.apply_selection(
                output_name=preserved_output.name,
                output_hostapi=preserved_output.hostapi,
            )

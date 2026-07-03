from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pipeline.session import AudioPlatform

logger = logging.getLogger(__name__)


class PluginsTab(QWidget):
    """VST3 plugin library — load, remove, and inspect plugins only."""

    plugins_changed = Signal()

    def __init__(self, platform: AudioPlatform) -> None:
        super().__init__()
        self._platform = platform
        self._build_ui()
        self._refresh_plugin_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        list_group = QGroupBox("Geladene Plugins")
        list_layout = QVBoxLayout(list_group)
        self.plugin_list = QListWidget()
        self.plugin_list.currentItemChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.plugin_list)

        buttons = QHBoxLayout()
        self.load_btn = QPushButton("Plugin laden…")
        self.unload_btn = QPushButton("Plugin entfernen")
        self.load_btn.clicked.connect(self._load_vst)
        self.unload_btn.clicked.connect(self._unload_vst)
        buttons.addWidget(self.load_btn)
        buttons.addWidget(self.unload_btn)
        list_layout.addLayout(buttons)
        layout.addWidget(list_group)

        info_group = QGroupBox("Plugin-Informationen")
        self.info_form = QFormLayout(info_group)
        self.info_name = QLabel("–")
        self.info_path = QLabel("–")
        self.info_path.setWordWrap(True)
        self.info_status = QLabel("–")
        self.info_params = QLabel("–")
        self.info_usage = QLabel("–")
        self.info_form.addRow("Name:", self.info_name)
        self.info_form.addRow("Pfad:", self.info_path)
        self.info_form.addRow("Status:", self.info_status)
        self.info_form.addRow("Parameter:", self.info_params)
        self.info_form.addRow("Verwendet in:", self.info_usage)
        layout.addWidget(info_group)

        hint = QLabel(
            "Plugins hier laden und entfernen. Parameter und Kettenreihenfolge "
            "bearbeitest du im Playback- bzw. Mikrofon-Tab."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        layout.addStretch()

    def _selected_plugin_id(self) -> str | None:
        item = self.plugin_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _plugin_usage(self, instance_id: str) -> str:
        routes: list[str] = []
        playback = any(
            s.kind == "vst" and s.effect_type == instance_id
            for s in self._platform.playback.chain.slots
        )
        microphone = any(
            s.kind == "vst" and s.effect_type == instance_id
            for s in self._platform.microphone.chain.slots
        )
        if playback:
            routes.append("Playback")
        if microphone:
            routes.append("Mikrofon")
        return ", ".join(routes) if routes else "Keiner Kette"

    def _refresh_plugin_list(self) -> None:
        selected_id = self._selected_plugin_id()
        self.plugin_list.clear()
        for plugin in self._platform.vst_host.plugins:
            item = QListWidgetItem(plugin.name)
            item.setData(Qt.ItemDataRole.UserRole, plugin.instance_id)
            self.plugin_list.addItem(item)
            if plugin.instance_id == selected_id:
                self.plugin_list.setCurrentItem(item)

        if self.plugin_list.currentItem() is None and self.plugin_list.count() > 0:
            self.plugin_list.setCurrentRow(0)
        elif self.plugin_list.count() == 0:
            self._clear_info()

    def _clear_info(self) -> None:
        self.info_name.setText("–")
        self.info_path.setText("–")
        self.info_status.setText("–")
        self.info_params.setText("–")
        self.info_usage.setText("–")

    def _on_selection_changed(self) -> None:
        instance_id = self._selected_plugin_id()
        if instance_id is None:
            self._clear_info()
            return

        entry = self._platform.vst_host.get_plugin(instance_id)
        if entry is None:
            self._clear_info()
            return

        params = self._platform.vst_host.get_parameters(instance_id)
        self.info_name.setText(entry.name)
        self.info_path.setText(entry.path)
        self.info_status.setText("Geladen" if entry.loaded else (entry.error or "Unbekannt"))
        self.info_params.setText(str(len(params)))
        self.info_usage.setText(self._plugin_usage(instance_id))

    def _load_vst(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "VST3-Plugin laden",
            "",
            "VST3 Plugins (*.vst3);;Alle Dateien (*.*)",
        )
        if not path:
            return
        try:
            entry = self._platform.vst_host.load_plugin(path)
        except (OSError, ValueError, RuntimeError, ImportError) as exc:
            QMessageBox.critical(self, "Laden fehlgeschlagen", str(exc))
            return

        logger.info("Plugin geladen: %s (%s)", entry.name, entry.instance_id)
        self._refresh_plugin_list()
        self.plugins_changed.emit()

    def _unload_vst(self) -> None:
        instance_id = self._selected_plugin_id()
        if instance_id is None:
            return

        if self._platform.playback_running or self._platform.microphone_running:
            QMessageBox.information(
                self,
                "Pipeline aktiv",
                "Stoppe alle Pipelines, bevor du ein Plugin entfernst.",
            )
            return

        entry = self._platform.vst_host.get_plugin(instance_id)
        name = entry.name if entry else instance_id

        for chain in (self._platform.playback.chain, self._platform.microphone.chain):
            chain.slots = [
                slot
                for slot in chain.slots
                if not (slot.kind == "vst" and slot.effect_type == instance_id)
            ]

        self._platform.vst_host.unload_plugin(instance_id)
        logger.info("Plugin entfernt: %s", name)
        self._refresh_plugin_list()
        self.plugins_changed.emit()

"""Standalone test for WindowsAudioManager — no audio pipeline."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from audio.windows_audio_manager import WindowsAudioDevice, WindowsAudioManager
from audio.windows_device_mapping import map_to_windows_device, strip_backend_labels


class WindowsAudioTestWindow(QMainWindow):
    def __init__(self, manager: WindowsAudioManager) -> None:
        super().__init__()
        self._manager = manager
        self.setWindowTitle("Windows Audio Manager Test")
        self.resize(560, 220)

        if not manager.is_supported():
            QMessageBox.critical(
                self,
                "Windows Audio Manager Test",
                "Windows audio management is only supported on Windows.",
            )
            sys.exit(1)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QLabel(
            "Isolated test for Windows default playback device control. "
            "No audio pipeline, no VB-Cable, no DeepFilterNet."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_selection_changed)
        form.addRow("Playback Output", self.device_combo)

        self.current_label = QLabel("—")
        self.current_label.setWordWrap(True)
        form.addRow("Current Windows Device", self.current_label)

        layout.addLayout(form)

        self.set_button = QPushButton("Set as Windows Default")
        self.set_button.clicked.connect(self._set_default)
        layout.addWidget(self.set_button)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self._reload_devices()

    def _reload_devices(self) -> None:
        devices = self._manager.enumerate_playback_devices()
        current = self._manager.get_default_playback()

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for device in devices:
            self.device_combo.addItem(device.name, device)
        self.device_combo.blockSignals(False)

        if current is not None:
            self.current_label.setText(current.name)
            for index in range(self.device_combo.count()):
                entry = self.device_combo.itemData(index)
                if isinstance(entry, WindowsAudioDevice) and entry.device_id == current.device_id:
                    self.device_combo.setCurrentIndex(index)
                    break
        else:
            self.current_label.setText("Not detected")

        self._on_selection_changed()

    def _selected_device(self) -> WindowsAudioDevice | None:
        data = self.device_combo.currentData()
        return data if isinstance(data, WindowsAudioDevice) else None

    def _on_selection_changed(self) -> None:
        selected = self._selected_device()
        if selected is None:
            self.set_button.setEnabled(False)
            return
        current = self._manager.get_default_playback()
        is_current = current is not None and current.device_id == selected.device_id
        self.set_button.setEnabled(not is_current)
        self.set_button.setText(
            "Already Windows Default" if is_current else "Set as Windows Default"
        )

    def _set_default(self) -> None:
        selected = self._selected_device()
        if selected is None:
            return

        ok = self._manager.set_default_playback(selected)
        current = self._manager.get_default_playback()

        if ok and current is not None and current.device_id == selected.device_id:
            self.status_label.setText(f"Success: Windows playback is now “{current.name}”.")
            self.current_label.setText(current.name)
            self._on_selection_changed()
            return

        self.status_label.setText(
            "Failed to set Windows default playback device. "
            "Try running as a normal user with audio permissions."
        )
        if current is not None:
            self.current_label.setText(current.name)


def run_console_test(manager: WindowsAudioManager, set_index: int | None = None) -> int:
    if not manager.is_supported():
        print("Windows audio management is only supported on Windows.")
        return 1

    print("=== Windows Playback Devices ===")
    devices = manager.enumerate_playback_devices()
    for index, device in enumerate(devices):
        print(f"  [{index}] {device.name}")
        print(f"       id={device.device_id}")

    current = manager.get_default_playback()
    print("\n=== Current Windows Default Playback ===")
    print(f"  {current.name if current else 'Not detected'}")
    if current:
        print(f"  id={current.device_id}")

    print("\n=== Windows Recording Devices ===")
    for index, device in enumerate(manager.enumerate_recording_devices()):
        print(f"  [{index}] {device.name}")

    recording = manager.get_default_recording()
    print("\n=== Current Windows Default Recording ===")
    print(f"  {recording.name if recording else 'Not detected'}")

    if not devices:
        print("\nNo playback devices found.")
        return 1

    if set_index is not None:
        if set_index < 0 or set_index >= len(devices):
            print(f"Invalid index {set_index}")
            return 1
        target = devices[set_index]
        print(f"\nSetting default playback to: {target.name}")
        ok = manager.set_default_playback(target)
        after = manager.get_default_playback()
        print(f"  set_default_playback returned: {ok}")
        print(f"  current default now: {after.name if after else 'None'}")
        return 0 if ok and after is not None and after.device_id == target.device_id else 1

    print("\n=== Name mapping samples ===")
    if devices:
        sample_labels = [
            f"{devices[0].name} — Windows WASAPI, 48000 Hz [18]",
            devices[0].name,
        ]
        for label in sample_labels:
            cleaned = strip_backend_labels(label)
            mapping = map_to_windows_device(label, devices)
            mapped = mapping.windows_device.name if mapping else "no match"
            print(f"  label: {label}")
            print(f"    cleaned: {cleaned}")
            print(f"    mapped:  {mapped} ({mapping.match_reason if mapping else '-'})")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test WindowsAudioManager")
    parser.add_argument(
        "--console",
        action="store_true",
        help="Run console enumeration test instead of the GUI",
    )
    parser.add_argument(
        "--set-index",
        type=int,
        default=None,
        help="Console only: set default playback to device index",
    )
    args = parser.parse_args()

    manager = WindowsAudioManager()

    if args.console:
        return run_console_test(manager, set_index=args.set_index)

    app = QApplication(sys.argv)
    window = WindowsAudioTestWindow(manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

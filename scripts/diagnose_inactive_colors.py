"""Diagnose why QSlider/QComboBox colors change when the window loses focus."""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QSlider, QVBoxLayout, QWidget

from features.stable.ui.theme import APP_STYLESHEET

RELEVANT_ROLES = (
    QPalette.ColorRole.Window,
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.Base,
    QPalette.ColorRole.AlternateBase,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.Button,
    QPalette.ColorRole.ButtonText,
    QPalette.ColorRole.Highlight,
    QPalette.ColorRole.HighlightedText,
    QPalette.ColorRole.Mid,
    QPalette.ColorRole.Dark,
    QPalette.ColorRole.Light,
    QPalette.ColorRole.Midlight,
    QPalette.ColorRole.Shadow,
    QPalette.ColorRole.Link,
    QPalette.ColorRole.LinkVisited,
    QPalette.ColorRole.PlaceholderText,
    QPalette.ColorRole.Accent,
)


def _color_name(color: QColor) -> str:
    return f"#{color.red():02x}{color.green():02x}{color.blue():02x}"


def dump_palette_diff(app: QApplication, label: str) -> list[str]:
    palette = app.palette()
    lines: list[str] = [f"\n=== {label} ==="]
    for role in RELEVANT_ROLES:
        active = palette.color(QPalette.ColorGroup.Active, role)
        inactive = palette.color(QPalette.ColorGroup.Inactive, role)
        if active != inactive:
            lines.append(
                f"{role.name}: Active={_color_name(active)} "
                f"Inactive={_color_name(inactive)}"
            )
    if len(lines) == 1:
        lines.append("(no differences in listed roles)")
    return lines


def dump_widget_palette(widget: QWidget, label: str) -> list[str]:
    palette = widget.palette()
    lines: list[str] = [f"\n=== {label} widget palette() ==="]
    for role in RELEVANT_ROLES:
        active = palette.color(QPalette.ColorGroup.Active, role)
        inactive = palette.color(QPalette.ColorGroup.Inactive, role)
        current = palette.color(QPalette.ColorGroup.Current, role)
        lines.append(
            f"{role.name}: Current={_color_name(current)} "
            f"Active={_color_name(active)} Inactive={_color_name(inactive)}"
        )
    return lines


class ProbeWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Inactive Color Probe")
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        self.combo.addItems(["Speakers — WASAPI", "Headphones — MME"])
        self.slider = QSlider()
        self.slider.setRange(0, 100)
        self.slider.setValue(70)
        self.slider.setObjectName("strengthSlider")
        layout.addWidget(self.combo)
        layout.addWidget(self.slider)
        self._logged_inactive = False

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._report("window state change")
        elif event.type() == QEvent.Type.ActivationChange:
            self._report("activation change")

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._report("focus in")

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self._report("focus out")

    def _report(self, reason: str) -> None:
        active = self.isActiveWindow()
        print(f"\n--- {reason}: isActiveWindow={active} ---")
        for line in dump_widget_palette(self.combo, "QComboBox"):
            print(line)
        for line in dump_widget_palette(self.slider, "QSlider"):
            print(line)


def main() -> int:
    app = QApplication(sys.argv)
    print(f"Style: {app.style().objectName()}")
    print(f"Platform: {app.platformName()}")
    for line in dump_palette_diff(app, "App palette before stylesheet"):
        print(line)

    app.setStyle("Fusion")
    for line in dump_palette_diff(app, "App palette after Fusion"):
        print(line)

    app.setStyleSheet(APP_STYLESHEET)
    for line in dump_palette_diff(app, "App palette after stylesheet"):
        print(line)

    window = ProbeWindow()
    window.resize(480, 140)
    window.show()

    def initial_report() -> None:
        print("\n--- initial active window ---")
        for line in dump_widget_palette(window.combo, "QComboBox"):
            print(line)

    QTimer.singleShot(300, initial_report)
    QTimer.singleShot(500, lambda: print(
        "\n>>> Click outside this window, then refocus terminal. "
        "Watch palette Current group on focus out."
    ))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""Dark application theme for Audio Guide v1.0."""

APP_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #e8e8e8;
}

QMainWindow, QWidget#centralRoot {
    background-color: #2b2b2b;
}

QWidget#routeCard {
    background-color: #323232;
    border: 1px solid #3f3f3f;
    border-radius: 8px;
}

QWidget#routeCard QWidget {
    background-color: transparent;
}

QLabel#uiIcon {
    background-color: transparent;
    padding: 0;
    margin: 0;
}

QWidget#layoutGap {
    background-color: transparent;
}

QLabel#routeCardTitle {
    color: #f2f2f2;
    font-size: 14px;
    font-weight: 600;
    padding: 0;
    margin: 0;
}

QLabel#routeFieldLabel {
    color: #b8b8b8;
    font-size: 13px;
    padding: 0;
    margin: 0;
}

QLabel {
    background-color: transparent;
    color: #e8e8e8;
}

QLabel#strengthValue {
    color: #c8c8c8;
    font-variant-numeric: tabular-nums;
}

QComboBox,
QComboBox:inactive {
    background-color: #3a3a3a;
    color: #e8e8e8;
    border: 1px solid #4a4a4a;
    border-radius: 6px;
    padding: 7px 36px 7px 12px;
    min-height: 28px;
}

QComboBox:hover,
QComboBox:inactive:hover {
    border-color: #5a5a5a;
    background-color: #3d3d3d;
}

QComboBox:focus,
QComboBox:inactive:focus {
    border-color: #6a6a6a;
}

QComboBox::drop-down,
QComboBox:inactive::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: none;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow,
QComboBox:inactive::down-arrow {
    width: 12px;
    height: 8px;
    image: url(data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='%23c8c8c8' d='M1.5 1.5 6 6l4.5-4.5'/></svg>);
}

QComboBox QAbstractItemView {
    background-color: #3a3a3a;
    color: #e8e8e8;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    selection-background-color: #4a6fa5;
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}

QCheckBox {
    spacing: 10px;
    color: #e8e8e8;
    padding: 2px 0;
}

QCheckBox#nrEnableCheck,
ToggleSwitch {
    spacing: 12px;
    color: #f2f2f2;
    font-size: 14px;
    font-weight: 600;
    padding: 6px 0;
    min-height: 28px;
}

ToggleSwitch::indicator {
    width: 42px;
    height: 22px;
    border: none;
    background: transparent;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #9a9a9a;
    border-radius: 3px;
    background-color: #3a3a3a;
}

QCheckBox::indicator:unchecked {
    border: 2px solid #9a9a9a;
    background-color: #3a3a3a;
}

QCheckBox::indicator:hover {
    border-color: #b8b8b8;
    background-color: #424242;
}

QCheckBox::indicator:unchecked:hover {
    border-color: #b8b8b8;
    background-color: #424242;
}

QCheckBox::indicator:checked {
    background-color: #4a7ec0;
    border: 2px solid #4a7ec0;
    image: url(data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 14 14'><path fill='none' stroke='%23ffffff' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' d='M3 7.5 5.8 10.2 11 4'/></svg>);
}

QCheckBox::indicator:disabled {
    background-color: #2f2f2f;
    border: 2px solid #666666;
}

QSlider::groove:horizontal,
QSlider:inactive::groove:horizontal {
    height: 4px;
    background: #454545;
    border-radius: 2px;
}

QSlider::sub-page:horizontal,
QSlider:inactive::sub-page:horizontal {
    background: #4a7ec0;
    border-radius: 2px;
}

QSlider::add-page:horizontal,
QSlider:inactive::add-page:horizontal {
    background: #454545;
    border-radius: 2px;
}

QSlider#strengthSlider::handle:horizontal,
QSlider#strengthSlider:inactive::handle:horizontal {
    image: none;
    width: 18px;
    height: 18px;
    min-width: 18px;
    min-height: 18px;
    margin: -7px 0;
    background: #f2f2f2;
    border: 1.5px solid #c0c0c0;
    border-radius: 9px;
}

QSlider#strengthSlider::handle:horizontal:hover,
QSlider#strengthSlider:inactive::handle:horizontal:hover {
    background: #ffffff;
    border: 1.5px solid #d8d8d8;
}

QPushButton {
    background-color: #404040;
    color: #e8e8e8;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 7px 16px;
}

QPushButton:hover {
    background-color: #4a4a4a;
    border-color: #6a6a6a;
}

QPushButton:pressed {
    background-color: #353535;
}

QStatusBar {
    background-color: #252525;
    border-top: 1px solid #3a3a3a;
    color: #c8c8c8;
}

QStatusBar QLabel {
    background-color: transparent;
    color: #c8c8c8;
    padding: 0 10px;
}

QFrame#statusSeparator {
    color: #4a4a4a;
    background-color: #4a4a4a;
    max-width: 1px;
}
"""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

# Fusion on Windows uses these roles for slider fill and control chrome.
# Inactive defaults to #1e1e1e while Active uses cyan Highlight/Accent.
_FOCUS_STABLE_PALETTE_ROLES = (
    QPalette.ColorRole.Highlight,
    QPalette.ColorRole.HighlightedText,
    QPalette.ColorRole.Accent,
)


def apply_focus_stable_palette(app: QApplication) -> None:
    """Mirror Active Highlight/Accent into Inactive so unfocused windows match."""
    palette = app.palette()
    active = QPalette.ColorGroup.Active
    inactive = QPalette.ColorGroup.Inactive
    for role in _FOCUS_STABLE_PALETTE_ROLES:
        palette.setColor(inactive, role, palette.color(active, role))
        palette.setBrush(inactive, role, palette.brush(active, role))
    app.setPalette(palette)

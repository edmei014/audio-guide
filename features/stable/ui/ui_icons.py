"""Font Awesome icons via QtAwesome for Clear Audio v1.0."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

ICON_SIZE = 17
ICON_SPACING = 6
# Shared across both route panels so label and control columns line up.
FORM_LABEL_COLUMN_WIDTH = 186
LABEL_COLUMN_MIN_WIDTH = 148
FORM_ROW_SPACING = 22
TITLE_SECTION_GAP = 10

COLOR_TITLE = "#f2f2f2"
COLOR_LABEL = "#b8b8b8"
COLOR_TEXT = "#e8e8e8"
COLOR_STATUS = "#c8c8c8"


def fa_icon(name: str, color: str, size: int = ICON_SIZE):
    return qta.icon(name, color=color)


def icon_label(name: str, color: str, size: int = ICON_SIZE) -> QLabel:
    label = QLabel()
    label.setPixmap(fa_icon(name, color, size).pixmap(size, size))
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setObjectName("uiIcon")
    return label


def icon_column_spacer() -> QWidget:
    """Fixed-width placeholder so rows without icons stay aligned."""
    spacer = QWidget()
    spacer.setFixedSize(ICON_SIZE, ICON_SIZE)
    return spacer


def vertical_gap(height: int) -> QWidget:
    gap = QWidget()
    gap.setFixedHeight(height)
    gap.setObjectName("layoutGap")
    return gap


def labeled_text_widget(
    text: str,
    icon_name: str | None,
    *,
    color: str = COLOR_LABEL,
    object_name: str | None = None,
) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(ICON_SPACING)
    if icon_name:
        layout.addWidget(icon_label(icon_name, color))
    text_label = QLabel(text)
    if object_name:
        text_label.setObjectName(object_name)
    layout.addWidget(text_label)
    layout.addStretch()
    return widget


class IconTextLabel(QWidget):
    """Compact icon + text row for the status bar."""

    def __init__(
        self,
        icon_name: str,
        text: str,
        *,
        color: str = COLOR_STATUS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(ICON_SPACING)
        layout.addWidget(icon_label(icon_name, color))
        self._text_label = QLabel(text)
        layout.addWidget(self._text_label)

    def text(self) -> str:
        return self._text_label.text()

    def setText(self, text: str) -> None:
        self._text_label.setText(text)

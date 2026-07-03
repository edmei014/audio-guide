"""Strength slider that can block user input without changing disabled styling."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider


class StrengthSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None) -> None:
        super().__init__(orientation, parent)
        self._interaction_locked = False

    def set_interaction_locked(self, locked: bool) -> None:
        self._interaction_locked = locked

    def interaction_locked(self) -> bool:
        return self._interaction_locked

    def mousePressEvent(self, event) -> None:
        if self._interaction_locked:
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._interaction_locked:
            event.ignore()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._interaction_locked:
            event.ignore()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        if self._interaction_locked:
            event.ignore()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        if self._interaction_locked:
            event.ignore()
            return
        super().keyPressEvent(event)

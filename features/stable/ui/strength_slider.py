"""Strength slider with groove-click positioning and read-only locking."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider


class StrengthSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None) -> None:
        super().__init__(orientation, parent)
        self._interaction_locked = False
        self.setTracking(True)

    def set_interaction_locked(self, locked: bool) -> None:
        self._interaction_locked = locked

    def interaction_locked(self) -> bool:
        return self._interaction_locked

    def _groove_geometry(self) -> tuple[object, QStyleOptionSlider]:
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        return groove, option

    def _value_from_position(self, position: QPointF) -> int:
        groove, option = self._groove_geometry()
        if self.orientation() == Qt.Orientation.Horizontal:
            pos = int(position.x()) - groove.x()
            span = groove.width()
        else:
            pos = int(position.y()) - groove.y()
            span = groove.height()
        if span <= 0:
            return self.value()
        return self.style().sliderValueFromPosition(
            self.minimum(),
            self.maximum(),
            pos,
            span,
            option.upsideDown,
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._interaction_locked:
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            handle = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider,
                option,
                QStyle.SubControl.SC_SliderHandle,
                self,
            )
            if not handle.contains(event.position().toPoint()):
                self.setValue(self._value_from_position(event.position()))
        super().mousePressEvent(event)

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

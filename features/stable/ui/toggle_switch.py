"""Modern ON/OFF toggle switch replacing the noise-reduction checkbox."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton

TRACK_WIDTH = 42
TRACK_HEIGHT = 22
THUMB_SIZE = 18
TRACK_RADIUS = TRACK_HEIGHT / 2
THUMB_MARGIN = 2

COLOR_TRACK_OFF = QColor("#454545")
COLOR_TRACK_ON = QColor("#4a7ec0")
COLOR_THUMB_OFF = QColor("#c8c8c8")
COLOR_THUMB_ON = QColor("#ffffff")


class ToggleSwitch(QCheckBox):
    """QCheckBox-compatible toggle switch with custom painting."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("nrEnableCheck")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumb_position = 1.0 if self.isChecked() else 0.0
        self._animation: QPropertyAnimation | None = None
        self.setStyleSheet(
            """
            ToggleSwitch::indicator {
                width: 42px;
                height: 22px;
                border: none;
                background: transparent;
            }
            """
        )

    def get_thumb_position(self) -> float:
        return self._thumb_position

    def set_thumb_position(self, value: float) -> None:
        self._thumb_position = value
        self.update()

    thumbPosition = Property(float, get_thumb_position, set_thumb_position)

    def setChecked(self, checked: bool) -> None:
        if self.isChecked() == checked:
            return
        super().setChecked(checked)
        self._animate_thumb(1.0 if checked else 0.0)

    def mouseReleaseEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.isEnabled()
            and self.rect().contains(event.pos())
        ):
            self.setChecked(not self.isChecked())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _animate_thumb(self, target: float) -> None:
        if self._animation is not None:
            self._animation.stop()
        self._animation = QPropertyAnimation(self, b"thumbPosition", self)
        self._animation.setDuration(120)
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(target)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    def _indicator_rect(self) -> QRectF:
        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            option,
            self,
        )
        return QRectF(rect)

    def _paint_switch(self, painter: QPainter, indicator: QRectF) -> None:
        track_rect = QRectF(
            indicator.x(),
            indicator.y() + (indicator.height() - TRACK_HEIGHT) / 2,
            TRACK_WIDTH,
            TRACK_HEIGHT,
        )
        thumb_travel = TRACK_WIDTH - THUMB_SIZE - (THUMB_MARGIN * 2)
        thumb_x = track_rect.x() + THUMB_MARGIN + (thumb_travel * self._thumb_position)
        thumb_y = track_rect.y() + (TRACK_HEIGHT - THUMB_SIZE) / 2
        thumb_rect = QRectF(thumb_x, thumb_y, THUMB_SIZE, THUMB_SIZE)

        track_color = QColor(COLOR_TRACK_ON if self.isChecked() else COLOR_TRACK_OFF)
        if not self.isChecked() and self._thumb_position > 0:
            track_color = self._blend_color(
                COLOR_TRACK_OFF,
                COLOR_TRACK_ON,
                self._thumb_position,
            )
        elif self.isChecked() and self._thumb_position < 1:
            track_color = self._blend_color(
                COLOR_TRACK_OFF,
                COLOR_TRACK_ON,
                self._thumb_position,
            )

        thumb_color = QColor(COLOR_THUMB_ON if self._thumb_position >= 0.5 else COLOR_THUMB_OFF)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, TRACK_RADIUS, TRACK_RADIUS)

        painter.setBrush(thumb_color)
        painter.drawEllipse(thumb_rect)

        if not self.isEnabled():
            painter.setPen(QPen(QColor(0, 0, 0, 60), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(track_rect, TRACK_RADIUS, TRACK_RADIUS)

    @staticmethod
    def _blend_color(start: QColor, end: QColor, amount: float) -> QColor:
        amount = max(0.0, min(1.0, amount))
        return QColor(
            int(start.red() + (end.red() - start.red()) * amount),
            int(start.green() + (end.green() - start.green()) * amount),
            int(start.blue() + (end.blue() - start.blue()) * amount),
        )

    def paintEvent(self, event) -> None:
        option = QStyleOptionButton()
        self.initStyleOption(option)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        indicator = self._indicator_rect()
        self._paint_switch(painter, indicator)

        option.rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxContents,
            option,
            self,
        )
        self.style().drawControl(
            QStyle.ControlElement.CE_CheckBoxLabel,
            option,
            painter,
            self,
        )

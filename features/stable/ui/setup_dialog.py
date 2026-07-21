"""First-run VB-Cable setup assistant."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from features.stable.ui.app_icon import apply_window_icon

VB_CABLE_URL = "https://vb-audio.com/Cable/"


class VbCableSetupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clear Audio Setup")
        apply_window_icon(self)
        self.setModal(True)
        self.resize(480, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QLabel("VB-Cable Required for Noise Reduction")
        title.setWordWrap(True)
        layout.addWidget(title)

        body = QLabel(
            "Clear Audio uses VB-Audio Virtual Cable to clean up what you hear and "
            "what you send before audio reaches your apps.\n\n"
            "VB-Cable was not detected on this system."
        )
        body.setWordWrap(True)
        layout.addWidget(body)

        button_row = QDialogButtonBox()
        self.download_button = QPushButton("Download VB-Cable")
        self.guide_button = QPushButton("Installation Guide")
        self.continue_button = QPushButton("Continue Anyway")
        button_row.addButton(self.download_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_row.addButton(self.guide_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_row.addButton(self.continue_button, QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(button_row)

        self.download_button.clicked.connect(self._open_download_page)
        self.guide_button.clicked.connect(self._show_installation_guide)
        self.continue_button.clicked.connect(self.accept)

    def _open_download_page(self) -> None:
        QDesktopServices.openUrl(QUrl(VB_CABLE_URL))

    def _show_installation_guide(self) -> None:
        QMessageBox.information(
            self,
            "VB-Cable Installation Guide",
            "1. Click Download VB-Cable to open the official VB-Audio website.\n"
            "2. Download and run the VB-Cable installer.\n"
            "3. Complete installation, then return to Clear Audio.\n"
            "4. Clear Audio will detect VB-Cable automatically within a few seconds.\n\n"
            "After installation, enable Noise Reduction in What You Hear "
            "to route PC audio through Clear Audio.",
        )

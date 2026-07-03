"""Application icon loading for Audio Guide."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
ICON_RELATIVE_PATH = Path("sources") / "audio-guide.ico"
ICON_PATH = _PROJECT_ROOT / ICON_RELATIVE_PATH
APP_USER_MODEL_ID = "AudioGuide.App"


def set_windows_app_user_model_id() -> None:
    """Assign a stable Windows AppUserModelID so the taskbar uses our icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        return


def application_icon() -> QIcon:
    if not ICON_PATH.is_file():
        return QIcon()
    return QIcon(str(ICON_PATH))


def apply_application_icon(app: QApplication) -> None:
    icon = application_icon()
    if icon.isNull():
        return
    app.setWindowIcon(icon)


def apply_window_icon(window: QWidget) -> None:
    icon = application_icon()
    if icon.isNull():
        return
    window.setWindowIcon(icon)

"""Application icon loading for Clear Audio."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
ICON_RELATIVE_PATH = Path("sources") / "audio-guide.ico"
ICON_FALLBACK_RELATIVE_PATH = Path("sources") / "logo.ico"
APP_USER_MODEL_ID = "ClearAudio.App"


def _resource_base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return _PROJECT_ROOT


def icon_resource_path() -> Path | None:
    """Return the application icon path for source runs and PyInstaller bundles."""
    base = _resource_base_path()
    primary = base / ICON_RELATIVE_PATH
    if primary.is_file():
        return primary

    fallback = base / ICON_FALLBACK_RELATIVE_PATH
    if fallback.is_file():
        return fallback

    return None


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
    path = icon_resource_path()
    if path is None:
        return QIcon()
    return QIcon(str(path))


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

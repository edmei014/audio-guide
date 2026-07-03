"""UI performance counters and periodic logging."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("audioguide.ui")


class UiActivityLog:
    def __init__(self) -> None:
        self.device_polls = 0
        self.device_refreshes = 0
        self.windows_sync_attempts = 0
        self.windows_sync_applied = 0
        self.status_updates = 0
        self.ui_updates = 0
        self._last_summary = time.monotonic()

    def record_device_poll(self, *, changed: bool) -> None:
        self.device_polls += 1
        logger.debug(
            "Device poll #%d (changed=%s)",
            self.device_polls,
            changed,
        )
        self._maybe_log_summary()

    def record_device_refresh(self, *, manual: bool) -> None:
        self.device_refreshes += 1
        logger.info(
            "Device refresh #%d (manual=%s)",
            self.device_refreshes,
            manual,
        )
        self._maybe_log_summary()

    def record_windows_sync(self, *, applied: bool) -> None:
        self.windows_sync_attempts += 1
        if applied:
            self.windows_sync_applied += 1
        logger.debug(
            "Windows sync attempt #%d (applied=%s)",
            self.windows_sync_attempts,
            applied,
        )
        self._maybe_log_summary()

    def record_status_update(self) -> None:
        self.status_updates += 1
        logger.debug("Status update #%d", self.status_updates)
        self._maybe_log_summary()

    def record_ui_update(self, reason: str) -> None:
        self.ui_updates += 1
        logger.debug("UI update #%d (%s)", self.ui_updates, reason)
        self._maybe_log_summary()

    def _maybe_log_summary(self) -> None:
        now = time.monotonic()
        if now - self._last_summary < 30.0:
            return
        self._last_summary = now
        logger.info(
            "UI activity (last 30s): polls=%d refreshes=%d "
            "windows_sync=%d/%d status_updates=%d ui_updates=%d",
            self.device_polls,
            self.device_refreshes,
            self.windows_sync_applied,
            self.windows_sync_attempts,
            self.status_updates,
            self.ui_updates,
        )


def configure_ui_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

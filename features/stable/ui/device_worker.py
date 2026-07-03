"""Background device scanning to keep the GUI thread responsive."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from audio.devices import DeviceEntry, list_devices_fast, list_usable_devices
from audio.device_utils import device_fingerprint


class DeviceScanSignals(QObject):
    finished = Signal(list, list, bool)
    failed = Signal(str)


class DeviceScanTask(QRunnable):
    def __init__(self, *, full_probe: bool) -> None:
        super().__init__()
        self._full_probe = full_probe
        self.signals = DeviceScanSignals()

    def run(self) -> None:
        try:
            if self._full_probe:
                inputs = list_usable_devices("input")
                outputs = list_usable_devices("output")
            else:
                inputs = list_devices_fast("input")
                outputs = list_devices_fast("output")
            self.signals.finished.emit(inputs, outputs, self._full_probe)
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class DevicePollController(QObject):
    """Coordinates fast background polls and full probes when hardware changes."""

    devices_refreshed = Signal(list, list)
    poll_completed = Signal(bool)
    scan_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._thread_pool = QThreadPool.globalInstance()
        self._input_fingerprint: tuple[tuple[str, str], ...] = ()
        self._output_fingerprint: tuple[tuple[str, str], ...] = ()
        self._busy = False

    def set_baselines(
        self,
        inputs: list[DeviceEntry],
        outputs: list[DeviceEntry],
    ) -> None:
        self._input_fingerprint = device_fingerprint(inputs)
        self._output_fingerprint = device_fingerprint(outputs)

    def is_busy(self) -> bool:
        return self._busy

    @Slot()
    def poll_fast(self) -> None:
        if self._busy:
            return
        self._start_scan(full_probe=False)

    @Slot()
    def refresh_full(self) -> None:
        if self._busy:
            return
        self._start_scan(full_probe=True)

    def _start_scan(self, *, full_probe: bool) -> None:
        self._busy = True
        task = DeviceScanTask(full_probe=full_probe)
        task.signals.finished.connect(self._on_scan_finished)
        task.signals.failed.connect(self._on_scan_failed)
        self._thread_pool.start(task)

    @Slot(list, list, bool)
    def _on_scan_finished(
        self,
        inputs: list[DeviceEntry],
        outputs: list[DeviceEntry],
        full_probe: bool,
    ) -> None:
        self._busy = False
        new_input_fp = device_fingerprint(inputs)
        new_output_fp = device_fingerprint(outputs)

        if full_probe:
            self._input_fingerprint = new_input_fp
            self._output_fingerprint = new_output_fp
            self.devices_refreshed.emit(inputs, outputs)
            return

        if (
            new_input_fp == self._input_fingerprint
            and new_output_fp == self._output_fingerprint
        ):
            self.poll_completed.emit(False)
            return

        self._start_scan(full_probe=True)

    @Slot(str)
    def _on_scan_failed(self, message: str) -> None:
        self._busy = False
        self.scan_failed.emit(message)

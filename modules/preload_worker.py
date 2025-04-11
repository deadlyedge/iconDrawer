import os
import logging
from typing import List, NamedTuple
from PySide6.QtCore import QObject, QRunnable, Slot, Signal


class FileInfo(NamedTuple):
    """Simple structure to hold basic file info for preloading."""

    name: str
    path: str
    is_dir: bool


class WorkerSignals(QObject):
    """Defines signals available from a running worker thread."""

    finished = Signal(str, list)  # drawer_path, list[FileInfo]
    error = Signal(str, str)  # drawer_path, error_message


class PreloadWorker(QRunnable):
    """Worker thread for preloading file list of a single drawer."""

    def __init__(self, drawer_path: str, signals: WorkerSignals):
        super().__init__()
        self.drawer_path = drawer_path
        self.signals = signals

    @Slot()
    def run(self):
        file_list: List[FileInfo] = []
        try:
            for entry in os.scandir(self.drawer_path):
                try:
                    file_list.append(
                        FileInfo(
                            name=entry.name, path=entry.path, is_dir=entry.is_dir()
                        )
                    )
                except OSError as e:
                    logging.warning(
                        f"Could not access entry {entry.name} in {self.drawer_path}: {e}"
                    )
            self.signals.finished.emit(self.drawer_path, file_list)
        except OSError as e:
            logging.error(f"Error scanning drawer {self.drawer_path}: {e}")
            self.signals.error.emit(self.drawer_path, str(e))

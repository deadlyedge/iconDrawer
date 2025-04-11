import logging
from PySide6.QtCore import QObject, QRunnable, Slot, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon
from .icon_utils import get_icon_for_path

class IconWorkerSignals(QObject):
    """Defines signals for the icon loading worker."""
    icon_loaded = Signal(QWidget, QIcon)  # widget instance, loaded icon
    error = Signal(str, str)  # file_path, error message

class IconLoadWorker(QRunnable):
    """Worker thread to load an icon for a specific file path."""
    def __init__(self, file_path: str, target_widget: QWidget, signals: IconWorkerSignals):
        super().__init__()
        self.file_path = file_path
        self.target_widget = target_widget
        self.signals = signals

    @Slot()
    def run(self):
        """Load the icon in the background."""
        try:
            icon = get_icon_for_path(self.file_path)
            if icon:
                self.signals.icon_loaded.emit(self.target_widget, icon)
            else:
                logging.warning(f"Icon loading returned None for: {self.file_path}")
        except Exception as e:
            logging.error(f"Error loading icon for {self.file_path}: {e}")
            self.signals.error.emit(self.file_path, str(e))

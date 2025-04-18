import logging
from typing import Optional
from PySide6.QtCore import QObject, QRunnable, Slot, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon

from .settings_manager import SettingsManager
from .icon_dispatcher import DefaultIconProvider, validate_path, IconDispatcher


_icon_provider: Optional[DefaultIconProvider] = None
_icon_dispatcher: Optional[IconDispatcher] = None
_unknown_icon: Optional[QIcon] = None
_initialized = False


class IconWorkerSignals(QObject):
    icon_loaded = Signal(QWidget, QIcon)
    error = Signal(str, str)


class IconLoadWorker(QRunnable):
    def __init__(
        self, file_path: str, target_widget: QWidget, signals: IconWorkerSignals
    ):
        super().__init__()
        self.file_path = file_path
        self.target_widget = target_widget
        self.signals = signals

    @Slot()
    def run(self):
        try:
            icon = get_icon_for_path(self.file_path)
            if icon:
                self.signals.icon_loaded.emit(self.target_widget, icon)
            else:
                logging.warning(f"Icon loading returned None for: {self.file_path}")
        except Exception as e:
            logging.error(f"Error loading icon for {self.file_path}: {e}")
            self.signals.error.emit(self.file_path, str(e))


def _initialize_icon_components():
    global _icon_provider, _icon_dispatcher, _unknown_icon, _initialized
    if _initialized:
        return

    try:
        (
            _,
            _,
            _,
            _,
            icon_folder_path,
            icon_file_theme,
            icon_unknown_theme,
            thumbnail_qsize,
        ) = SettingsManager.load_settings()

        _icon_provider = DefaultIconProvider(
            folder_icon_path=icon_folder_path,
            file_icon_theme=icon_file_theme,
            unknown_icon_theme=icon_unknown_theme,
        )
        _icon_dispatcher = IconDispatcher(_icon_provider, thumbnail_qsize)
        _unknown_icon = _icon_provider.get_unknown_icon()

        _initialized = True
        logging.debug("Icon components initialized successfully using settings.")
    except Exception as e:
        logging.critical(f"Failed to initialize icon components: {e}", exc_info=True)
        _icon_provider = None
        _icon_dispatcher = None
        _unknown_icon = QIcon()
        _initialized = True


def get_icon_for_path(full_path: str) -> QIcon:
    _initialize_icon_components()

    local_unknown_icon = _unknown_icon if _unknown_icon is not None else QIcon()
    local_icon_dispatcher = _icon_dispatcher

    if not local_icon_dispatcher:
        logging.error("Icon dispatcher not available, returning fallback icon.")
        return local_unknown_icon

    validated_path_info = validate_path(full_path)
    if not validated_path_info:
        logging.debug(
            f"Path validation failed for '{full_path}', returning fallback icon."
        )
        return local_unknown_icon

    try:
        icon = local_icon_dispatcher.dispatch(validated_path_info)
        return icon if icon and not icon.isNull() else local_unknown_icon
    except Exception as e:
        logging.error(
            f"Error during icon dispatch for path '{full_path}': {e}", exc_info=True
        )
        return local_unknown_icon

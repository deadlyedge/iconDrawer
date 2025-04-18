import logging
from typing import Optional
from PySide6.QtCore import QObject, QRunnable, Slot, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon

from .settings_manager import SettingsManager
from .icon_dispatcher import DefaultIconProvider, validate_path, IconDispatcher


# --- Global Variables (Lazy Initialized) ---
_icon_provider: Optional[DefaultIconProvider] = None
_icon_dispatcher: Optional[IconDispatcher] = None
_unknown_icon: Optional[QIcon] = None  # Fallback unknown icon
_initialized = False  # For custom components initialization


class IconWorkerSignals(QObject):
    """Defines signals for the icon loading worker."""

    icon_loaded = Signal(QWidget, QIcon)  # widget instance, loaded icon
    error = Signal(str, str)  # file_path, error message


class IconLoadWorker(QRunnable):
    """Worker thread to load an icon for a specific file path."""

    def __init__(
        self, file_path: str, target_widget: QWidget, signals: IconWorkerSignals
    ):
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


# --- Initialization Function (for custom components) ---
# Removed global _qt_icon_provider instance
def _initialize_icon_components():
    """Initializes the icon components using loaded settings only when needed."""
    global _icon_provider, _icon_dispatcher, _unknown_icon, _initialized
    if _initialized:
        return

    try:
        # Load all settings
        (
            _,  # drawers (not needed here)
            _,  # window_pos (not needed here)
            _,  # bg_color (not needed here)
            _,  # start_flag (not needed here)
            icon_folder_path,
            icon_file_theme,
            icon_unknown_theme,
            thumbnail_qsize,
        ) = SettingsManager.load_settings()

        # Initialize provider with loaded settings
        _icon_provider = DefaultIconProvider(
            folder_icon_path=icon_folder_path,
            file_icon_theme=icon_file_theme,
            unknown_icon_theme=icon_unknown_theme,
        )
        # Initialize dispatcher with provider and thumbnail size
        _icon_dispatcher = IconDispatcher(_icon_provider, thumbnail_qsize)
        # Get the unknown icon from the initialized provider
        _unknown_icon = _icon_provider.get_unknown_icon()

        _initialized = True
        logging.debug("Icon components initialized successfully using settings.")
    except Exception as e:
        logging.critical(f"Failed to initialize icon components: {e}", exc_info=True)
        # Ensure fallbacks are set even on error
        _icon_provider = None
        _icon_dispatcher = None
        _unknown_icon = QIcon()  # Basic empty icon
        _initialized = True  # Mark as initialized to prevent retries


# --- Public API ---
def get_icon_for_path(full_path: str) -> QIcon:
    """
    Gets the appropriate QIcon for a given file system path using a
    refactored validator/dispatcher/worker pattern.

    Args:
        full_path: The absolute path to the file or directory.

    Returns:
        The most appropriate QIcon found, or a default unknown icon if
        the path is invalid or no specific icon could be determined.
    """
    # Ensure custom components (like dispatcher) are initialized if needed
    # The dispatcher will now handle the logic including QFileIconProvider and fallbacks
    _initialize_icon_components()

    # Use the initialized components (or fallbacks if init failed)
    # Add checks for None in case initialization failed critically
    local_unknown_icon = _unknown_icon if _unknown_icon is not None else QIcon()
    local_icon_dispatcher = _icon_dispatcher

    if not local_icon_dispatcher:
        logging.error("Icon dispatcher not available, returning fallback icon.")
        return local_unknown_icon

    # Get necessary components (or fallbacks)
    local_unknown_icon = _unknown_icon if _unknown_icon is not None else QIcon()
    local_icon_dispatcher = _icon_dispatcher

    if not local_icon_dispatcher:
        logging.error("Icon dispatcher not available, returning fallback icon.")
        return local_unknown_icon

    # 1. Validate the path first (using the standard validator)
    # It's better to validate once before dispatching
    validated_path_info = validate_path(full_path)
    if not validated_path_info:
        logging.debug(
            f"Path validation failed for '{full_path}', returning fallback icon."
        )
        return local_unknown_icon  # Return fallback icon if path is invalid

    # 2. Call the dispatcher with the validated info
    try:
        icon = local_icon_dispatcher.dispatch(validated_path_info)
        # Dispatcher should handle its own logging and fallbacks internally now
        # Return the icon from the dispatcher, or the unknown icon if dispatch failed
        return icon if icon and not icon.isNull() else local_unknown_icon

    except Exception as e:
        logging.error(
            f"Error during icon dispatch for path '{full_path}': {e}",
            exc_info=True,  # Include stack trace in log
        )
        return local_unknown_icon  # Return fallback icon on unexpected error

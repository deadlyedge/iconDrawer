import logging
from typing import Optional
from PySide6.QtGui import QIcon
# QFileIconProvider will be used within the dispatcher now
# from PySide6.QtWidgets import QFileIconProvider
# from PySide6.QtCore import QFileInfo

# Import the refactored components
from .icon_provider import DefaultIconProvider # Keep for fallback initialization
from .icon_validators import validate_path
from .icon_dispatcher import IconDispatcher

# --- Global Variables (Lazy Initialized) ---
_icon_provider: Optional[DefaultIconProvider] = None
_icon_dispatcher: Optional[IconDispatcher] = None
_unknown_icon: Optional[QIcon] = None # Fallback unknown icon
_initialized = False # For custom components initialization

# --- Initialization Function (for custom components) ---
# Removed global _qt_icon_provider instance
def _initialize_icon_components():
    """Initializes the icon components only when needed."""
    global _icon_provider, _icon_dispatcher, _unknown_icon, _initialized
    if _initialized:
        return

    try:
        _icon_provider = DefaultIconProvider()
        _icon_dispatcher = IconDispatcher(_icon_provider)
        _unknown_icon = _icon_provider.get_unknown_icon()
        _initialized = True
        logging.debug("Icon components initialized successfully.")
    except Exception as e:
        logging.critical(f"Failed to initialize icon components: {e}", exc_info=True)
        # Ensure fallbacks are set even on error
        _icon_provider = None
        _icon_dispatcher = None
        _unknown_icon = QIcon() # Basic empty icon
        _initialized = True # Mark as initialized to prevent retries

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
        logging.debug(f"Path validation failed for '{full_path}', returning fallback icon.")
        return local_unknown_icon # Return fallback icon if path is invalid

    # 2. Call the dispatcher with the validated info
    try:
        icon = local_icon_dispatcher.dispatch(validated_path_info)
        # Dispatcher should handle its own logging and fallbacks internally now
        # Return the icon from the dispatcher, or the unknown icon if dispatch failed
        return icon if icon and not icon.isNull() else local_unknown_icon

    except Exception as e:
        logging.error(
            f"Error during icon dispatch for path '{full_path}': {e}",
            exc_info=True # Include stack trace in log
        )
        return local_unknown_icon # Return fallback icon on unexpected error

# --- Cleanup ---
# (No explicit cleanup needed for these components in this structure)

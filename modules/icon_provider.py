import os
import logging
from typing import Optional, Dict
from PySide6.QtGui import QIcon

# Dictionary to hold default icons, initialized lazily
DEFAULT_ICONS: dict[str, Optional[QIcon]] = {
    "folder": None,
    "file": None,  # Generic file
    "unknown": None,
    # --- Placeholder for future extension-specific default icons ---
    # ".txt": None,
    # ".pdf": None,
    # ".jpg": None,
    # -------------------------------------------------------------
}
_DEFAULT_ICONS_INITIALIZED = False


class DefaultIconProvider:
    """Manages and provides default QIcon objects."""

    def __init__(self):
        self._initialize_default_icons()

    def _initialize_default_icons(self):
        """Creates the default QIcon objects if they haven't been created yet."""
        global _DEFAULT_ICONS_INITIALIZED, DEFAULT_ICONS
        if _DEFAULT_ICONS_INITIALIZED:
            return

        # Default Folder Icon
        folder_icon_path = "asset/icons/folder_icon.png"
        if os.path.exists(folder_icon_path):
            DEFAULT_ICONS["folder"] = QIcon(folder_icon_path)
        else:
            logging.warning(
                f"Default folder icon not found at: {folder_icon_path}. Using fallback."
            )
            DEFAULT_ICONS["folder"] = QIcon.fromTheme("folder", QIcon())

        # Default Generic File Icon
        DEFAULT_ICONS["file"] = QIcon.fromTheme(
            "text-x-generic",
            QIcon(
                ":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png"
            ),
        )

        # Default Unknown Icon
        DEFAULT_ICONS["unknown"] = QIcon.fromTheme(
            "unknown",
            QIcon(
                ":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png"
            ),
        )

        # --- Initialize future extension-specific icons here if needed ---
        # Example:
        # txt_icon_path = "asset/icons/txt_icon.png"
        # if os.path.exists(txt_icon_path):
        #     DEFAULT_ICONS[".txt"] = QIcon(txt_icon_path)
        # else:
        #     DEFAULT_ICONS[".txt"] = DEFAULT_ICONS["file"] # Fallback to generic file
        # -------------------------------------------------------------

        _DEFAULT_ICONS_INITIALIZED = True
        logging.debug("Default icons initialized.")

    def get_icon(self, icon_type: str) -> QIcon:
        """Gets a specific default icon by type."""
        return DEFAULT_ICONS.get(icon_type) or self.get_unknown_icon()

    def get_folder_icon(self) -> QIcon:
        """Gets the default folder icon."""
        return DEFAULT_ICONS.get("folder") or self.get_unknown_icon()

    def get_file_icon(self) -> QIcon:
        """Gets the default generic file icon."""
        return DEFAULT_ICONS.get("file") or self.get_unknown_icon()

    def get_unknown_icon(self) -> QIcon:
        """Gets the default unknown icon."""
        # Ensure a basic QIcon is returned if 'unknown' somehow fails
        return DEFAULT_ICONS.get("unknown") or QIcon()

    def get_icon_for_extension(self, extension: str) -> Optional[QIcon]:
        """Gets a default icon based on file extension (case-insensitive)."""
        return DEFAULT_ICONS.get(extension.lower())

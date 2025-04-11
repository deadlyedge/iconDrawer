import os
import logging
from typing import Optional
from PySide6.QtGui import QIcon

# Dictionary to hold default icons
DEFAULT_ICONS: dict[str, Optional[QIcon]] = {}
# No longer lazy initialized globally, instance will handle it


class DefaultIconProvider:
    """Manages and provides default QIcon objects based on loaded settings."""

    def __init__(
        self, folder_icon_path: str, file_icon_theme: str, unknown_icon_theme: str
    ):
        """
        Initializes the provider with paths/themes from settings.

        Args:
            folder_icon_path: Path to the default folder icon.
            file_icon_theme: Theme name for the generic file icon.
            unknown_icon_theme: Theme name for the unknown icon.
        """
        self._initialize_default_icons(
            folder_icon_path, file_icon_theme, unknown_icon_theme
        )

    def _initialize_default_icons(
        self, folder_icon_path: str, file_icon_theme: str, unknown_icon_theme: str
    ):
        """Creates the default QIcon objects based on provided settings."""
        global DEFAULT_ICONS  # Modify the global dict (or make it instance specific if preferred)
        DEFAULT_ICONS.clear()  # Clear previous icons if re-initializing

        # Default Folder Icon
        if os.path.exists(folder_icon_path):
            DEFAULT_ICONS["folder"] = QIcon(folder_icon_path)
        else:
            logging.warning(
                f"Default folder icon not found at configured path: {folder_icon_path}. Using theme fallback."
            )
            # Fallback to theme icon if path is invalid
            DEFAULT_ICONS["folder"] = QIcon.fromTheme(
                "folder", QIcon()
            )  # Use basic QIcon() as final fallback

        # Default Generic File Icon
        # Use basic QIcon() as final fallback if theme icon is null
        DEFAULT_ICONS["file"] = QIcon.fromTheme(file_icon_theme, QIcon())

        # Default Unknown Icon
        # Use basic QIcon() as final fallback if theme icon is null
        DEFAULT_ICONS["unknown"] = QIcon.fromTheme(unknown_icon_theme, QIcon())

        # --- Initialize future extension-specific icons here if needed ---
        # Example using settings:
        # txt_icon_path = settings.get("txt_icon_path", "asset/icons/txt_icon.png")
        # if os.path.exists(txt_icon_path):
        #     DEFAULT_ICONS[".txt"] = QIcon(txt_icon_path)
        # else:
        #     DEFAULT_ICONS[".txt"] = DEFAULT_ICONS.get("file") # Fallback to generic file
        # -------------------------------------------------------------

        logging.debug("Default icons initialized using settings.")

    def get_icon(self, icon_type: str) -> QIcon:
        """Gets a specific default icon by type."""
        # Ensure a basic QIcon is returned if type is unknown or init failed
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

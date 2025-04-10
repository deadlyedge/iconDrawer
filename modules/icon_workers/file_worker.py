import logging
from typing import Optional
from PySide6.QtGui import QIcon
from .base_worker import BaseIconWorker
from ..icon_provider import DefaultIconProvider
from ..icon_validators import ValidatedPathInfo
from .utils import try_get_icon  # Import the helper function


class FileIconWorker(BaseIconWorker):
    """Worker responsible for retrieving icons for standard files."""

    def get_icon(
        self, path_info: ValidatedPathInfo, icon_provider: DefaultIconProvider
    ) -> Optional[QIcon]:
        """
        Attempts to retrieve an icon for a standard file.

        Checks for extension-specific default icons first, then tries
        to load the icon directly from the file path.

        Args:
            path_info: Validated path information for the file.
            icon_provider: The provider for default icons.

        Returns:
            A QIcon object if found, otherwise None (dispatcher will handle fallback).
        """
        full_path = path_info["full_path"]
        extension = path_info["extension"]

        # 1. Check for specific default icon based on extension
        if extension:
            specific_icon = icon_provider.get_icon_for_extension(extension)
            if specific_icon:
                logging.debug(f"Using extension-specific default icon for: {extension}")
                return specific_icon

        # 2. Try loading icon directly from the file path using helper
        # This might work for image files or files with embedded icons recognized by Qt
        std_icon = try_get_icon(full_path)
        if std_icon:
            logging.debug(f"Successfully loaded icon directly from file: {full_path}")
            return std_icon

        # 3. If no specific default and direct loading fails, return None
        # The dispatcher will handle falling back to the generic file icon.
        logging.debug(f"No specific or direct icon found for file: {full_path}")
        return None

import sys
import logging
from typing import Optional
from PySide6.QtGui import QIcon

from .icon_provider import DefaultIconProvider
from .icon_validators import ValidatedPathInfo
from .icon_workers.directory_worker import DirectoryIconWorker
from .icon_workers.lnk_worker import LnkIconWorker, _HAS_LNKPARSE # Import check flag
from .icon_workers.file_worker import FileIconWorker


class IconDispatcher:
    """Dispatches icon retrieval tasks to appropriate workers."""

    def __init__(self, icon_provider: DefaultIconProvider):
        """
        Initializes the dispatcher with an icon provider and worker instances.

        Args:
            icon_provider: An instance of DefaultIconProvider.
        """
        self.icon_provider = icon_provider
        self.directory_worker = DirectoryIconWorker()
        self.lnk_worker = LnkIconWorker()
        self.file_worker = FileIconWorker()
        # Add other workers here if needed in the future

    def dispatch(self, path_info: ValidatedPathInfo) -> Optional[QIcon]:
        """
        Selects the appropriate worker based on path info and retrieves the icon.

        Args:
            path_info: Dictionary containing validated path details.

        Returns:
            A QIcon object if a worker successfully retrieves one, otherwise None.
            Handles fallback to generic file icon internally for file types.
        """
        path_type = path_info["path_type"]
        extension = path_info["extension"]
        icon: Optional[QIcon] = None

        if path_type == "directory":
            icon = self.directory_worker.get_icon(path_info, self.icon_provider)
            # logging.debug(f"Dispatched to DirectoryWorker for: {path_info['full_path']}")

        elif path_type == "file":
            # Special handling for .lnk files on Windows
            if sys.platform == "win32" and extension == ".lnk" and _HAS_LNKPARSE:
                # logging.debug(f"Attempting LnkWorker for: {path_info['full_path']}")
                icon = self.lnk_worker.get_icon(path_info, self.icon_provider)
                if icon:
                    # logging.debug(f"LnkWorker succeeded for: {path_info['full_path']}")
                    return icon # Return immediately if LNK worker found icon
                # else:
                    # logging.debug(f"LnkWorker failed, falling back to FileWorker for: {path_info['full_path']}")

            # If not a .lnk, or if LnkWorker failed, use the standard FileWorker
            # logging.debug(f"Dispatching to FileWorker for: {path_info['full_path']}")
            icon = self.file_worker.get_icon(path_info, self.icon_provider)

            # If FileWorker (or LnkWorker fallback) didn't find an icon, use generic file icon
            if not icon:
                # logging.debug(f"FileWorker failed, using generic file icon for: {path_info['full_path']}")
                return self.icon_provider.get_file_icon()

        # else: # path_type == "unknown" or other cases
            # logging.debug(f"Unknown path type or worker failed for: {path_info['full_path']}")
            # Let the caller handle the final 'unknown' icon fallback

        return icon

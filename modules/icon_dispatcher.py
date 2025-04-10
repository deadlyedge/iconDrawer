import sys
import logging
from typing import Optional
from PySide6.QtCore import QFileInfo # Import QFileInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider # Import QFileIconProvider

from .icon_provider import DefaultIconProvider
from .icon_validators import ValidatedPathInfo
from .icon_workers.directory_worker import DirectoryIconWorker
from .icon_workers.lnk_worker import LnkIconWorker, _HAS_LNKPARSE # Import check flag
from .icon_workers.file_worker import FileIconWorker
from .icon_workers.thumbnail_worker import ThumbnailWorker # Import new worker


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
        self.thumbnail_worker = ThumbnailWorker() # Instantiate ThumbnailWorker
        self._qt_icon_provider = QFileIconProvider() # Instantiate QFileIconProvider
        # Add other workers here if needed in the future

    def dispatch(self, path_info: ValidatedPathInfo) -> Optional[QIcon]:
        """
        Selects the appropriate worker based on path info and retrieves the icon.

        Args:
            path_info: Dictionary containing validated path details.

        Returns:
            A QIcon object if a worker successfully retrieves one, otherwise None.
            Handles fallback to generic file icon internally if needed.
        """
        full_path = path_info["full_path"]
        path_type = path_info["path_type"]
        extension = path_info["extension"]
        icon: Optional[QIcon] = None

        logging.debug(f"Dispatching icon request for: {full_path} (Type: {path_type}, Ext: {extension})")

        # --- Priority 1: Thumbnail (Files only) ---
        if path_type == "file":
            if self.thumbnail_worker.can_handle(path_info):
                logging.debug(f"Attempting ThumbnailWorker for: {full_path}")
                icon = self.thumbnail_worker.get_icon(path_info)
                if icon and not icon.isNull():
                    logging.debug(f"ThumbnailWorker succeeded for: {full_path}")
                    return icon
                else:
                    logging.debug(f"ThumbnailWorker failed or returned null for: {full_path}")

        # --- Priority 2: LNK (Files only, Windows only) ---
        if path_type == "file" and sys.platform == "win32" and extension == ".lnk" and _HAS_LNKPARSE:
            logging.debug(f"Attempting LnkWorker for: {full_path}")
            icon = self.lnk_worker.get_icon(path_info, self.icon_provider)
            if icon and not icon.isNull():
                logging.debug(f"LnkWorker succeeded for: {full_path}")
                return icon
            else:
                logging.debug(f"LnkWorker failed or returned null for: {full_path}")

        # --- Priority 3: QFileIconProvider (Files and Directories) ---
        try:
            logging.debug(f"Attempting QFileIconProvider for: {full_path}")
            file_info = QFileInfo(full_path)
            qt_icon = self._qt_icon_provider.icon(file_info)
            if not qt_icon.isNull():
                 # Check available sizes (optional, for debugging)
                 # available_sizes = qt_icon.availableSizes()
                 # logging.debug(f"QFileIconProvider returned icon for '{full_path}'. Available sizes: {available_sizes}")
                 # Check available sizes (optional, for debugging)
                 # available_sizes = qt_icon.availableSizes()
                 # logging.debug(f"QFileIconProvider returned icon for '{full_path}'. Available sizes: {available_sizes}")
                 logging.debug(f"QFileIconProvider succeeded for: {full_path}")
                 return qt_icon
            else:
                 logging.debug(f"QFileIconProvider returned null icon for: {full_path}")
        except Exception as e:
            logging.error(f"Error calling QFileIconProvider for '{full_path}': {e}", exc_info=True)

        # --- Priority 4: DirectoryWorker (Directories only) ---
        if path_type == "directory":
            logging.debug(f"Attempting DirectoryWorker for: {full_path}")
            icon = self.directory_worker.get_icon(path_info, self.icon_provider)
            if icon and not icon.isNull():
                 logging.debug(f"DirectoryWorker succeeded for: {full_path}")
                 return icon
            else:
                 logging.debug(f"DirectoryWorker failed or returned null for: {full_path}")


        # --- Priority 5: FileWorker (Files only, final file fallback before generic) ---
        if path_type == "file":
            # This is reached if Thumbnail, LNK, and QFileIconProvider failed for a file
            logging.debug(f"Attempting FileWorker as fallback for: {full_path}")
            icon = self.file_worker.get_icon(path_info, self.icon_provider)
            if icon and not icon.isNull():
                 logging.debug(f"FileWorker succeeded for: {full_path}")
                 return icon
            else:
                 # If FileWorker also fails, return the generic file icon
                 logging.debug(f"FileWorker failed, returning generic file icon for: {full_path}")
                 return self.icon_provider.get_file_icon() # Use generic file icon

        # --- Final Fallback ---
        # If it's not a file or directory, or all workers failed for a directory
        logging.warning(f"All icon retrieval methods failed for: {full_path}. Returning None.")
        return None # Let icon_utils handle the final unknown icon

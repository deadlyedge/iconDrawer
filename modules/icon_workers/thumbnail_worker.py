import logging
import os
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QImageReader, QPixmap
# from PySide6.QtWidgets import QApplication # Might need for DPI scaling later

from ..icon_validators import ValidatedPathInfo
from .base_worker import BaseIconWorker

# Consider making this configurable later
DEFAULT_THUMBNAIL_SIZE = QSize(64, 64)
# Common image file extensions (case-insensitive)
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp",
}

class ThumbnailWorker(BaseIconWorker):
    """
    Generates thumbnail icons for image files.
    """

    def __init__(self, target_size: QSize = DEFAULT_THUMBNAIL_SIZE):
        self.target_size = target_size
        # QImageReader supports many formats out of the box

    def can_handle(self, path_info: ValidatedPathInfo) -> bool:
        """Checks if the path points to a supported image file."""
        # Access using dictionary keys
        if path_info['path_type'] != "file":
            return False
        # 'exists' check is implicitly done by validate_path returning non-None
        extension = path_info['extension']
        return extension is not None and extension in SUPPORTED_IMAGE_EXTENSIONS

    def get_icon(self, path_info: ValidatedPathInfo) -> Optional[QIcon]:
        """Attempts to read the image and create a scaled thumbnail icon."""
        if not self.can_handle(path_info):
            # This check is technically redundant if dispatch logic calls can_handle first,
            # but good for robustness if worker is called directly.
            return None

        file_path = path_info['full_path'] # Get the path using key
        logging.debug(f"ThumbnailWorker attempting to generate thumbnail for: {file_path}")
        try:
            reader = QImageReader(file_path)
            if not reader.canRead():
                logging.warning(f"ThumbnailWorker: QImageReader cannot read file: {file_path}, Error: {reader.errorString()}")
                return None

            # Set a smaller target size for reading if possible (efficiency)
            # Consider device pixel ratio for high DPI displays later if needed
            reader.setAutoTransform(True) # Apply EXIF orientation etc.

            # Read the image
            img = reader.read()
            if img.isNull():
                logging.warning(f"ThumbnailWorker: QImageReader failed to read image data from: {file_path}, Error: {reader.errorString()}")
                return None

            # Scale the image smoothly to fit the target size, keeping aspect ratio
            scaled_img = img.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            if scaled_img.isNull():
                 logging.warning(f"ThumbnailWorker: Failed to scale image for: {file_path}")
                 return None

            # Create QIcon from the scaled QPixmap
            pixmap = QPixmap.fromImage(scaled_img)
            if not pixmap.isNull():
                logging.debug(f"ThumbnailWorker successfully generated thumbnail for: {file_path}")
                return QIcon(pixmap)
            else:
                 logging.warning(f"ThumbnailWorker: Failed to create QPixmap from scaled image for: {file_path}")
                 return None

        except Exception as e:
            logging.error(f"ThumbnailWorker: Error generating thumbnail for {file_path}: {e}", exc_info=True)
            return None

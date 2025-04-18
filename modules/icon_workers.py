import os
import sys
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ValidationError

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QImageReader, QPixmap

try:
    import LnkParse3

    _HAS_LNKPARSE = True
except ImportError:
    logging.warning("LnkParse3 not found. .lnk file targets cannot be resolved.")
    _HAS_LNKPARSE = False


SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
}


class BaseIconWorker(ABC):
    """Abstract base class for icon retrieval workers."""

    @abstractmethod
    def get_icon(
        self, path_info: Dict[str, Any], icon_provider: Any
    ) -> Optional[QIcon]:
        """Attempts to retrieve an icon based on the validated path information."""
        pass


class DirectoryIconWorker(BaseIconWorker):
    """Worker responsible for providing the icon for directories."""

    def get_icon(
        self, path_info: Dict[str, Any], icon_provider: Any
    ) -> Optional[QIcon]:
        return icon_provider.get_folder_icon()


class FileIconWorker(BaseIconWorker):
    """Worker responsible for retrieving icons for standard files."""

    def get_icon(
        self, path_info: Dict[str, Any], icon_provider: Any
    ) -> Optional[QIcon]:
        full_path = path_info["full_path"]
        extension = path_info["extension"]

        if extension:
            specific_icon = icon_provider.get_icon_for_extension(extension)
            if specific_icon:
                logging.debug(f"Using extension-specific default icon for: {extension}")
                return specific_icon

        std_icon = try_get_icon(full_path)
        if std_icon:
            logging.debug(f"Successfully loaded icon directly from file: {full_path}")
            return std_icon

        logging.debug(f"No specific or direct icon found for file: {full_path}")
        return None


class LnkIconLocationBlock(BaseModel):
    target_unicode: Optional[str] = None


class LnkExtraData(BaseModel):
    icon_location_block: Optional[LnkIconLocationBlock] = Field(
        None, alias="ICON_LOCATION_BLOCK"
    )


class LnkLinkData(BaseModel):
    icon_location: Optional[str] = None
    working_directory: Optional[str] = None
    relative_path: Optional[str] = None
    absolute_path: Optional[str] = None


class LnkJsonModel(BaseModel):
    data: Optional[LnkLinkData] = None
    extra: Optional[LnkExtraData] = None


class LnkIconWorker(BaseIconWorker):
    """Worker responsible for extracting icons from .lnk shortcut files."""

    def get_icon(
        self, path_info: Dict[str, Any], icon_provider: Any
    ) -> Optional[QIcon]:
        full_path = path_info["full_path"]

        if not _HAS_LNKPARSE or sys.platform != "win32":
            logging.debug(
                "LnkParse3 not available or not on Windows, skipping LNK processing."
            )
            return None

        lnk_icon: Optional[QIcon] = None
        target_path: Optional[str] = None

        try:
            with open(full_path, "rb") as infile:
                raw_json_data: Dict[str, Any] = LnkParse3.lnk_file(infile).get_json()

            try:
                lnk_data = LnkJsonModel.model_validate(raw_json_data)
            except ValidationError as val_err:
                logging.warning(
                    f"Validation failed for LnkParse3 data from '{full_path}': {val_err}"
                )
                lnk_data = LnkJsonModel()

            if lnk_data.data and lnk_data.data.icon_location:
                lnk_icon = try_get_icon(lnk_data.data.icon_location)
                if lnk_icon:
                    logging.debug(
                        f"LNK icon found via data.icon_location: {lnk_data.data.icon_location}"
                    )

            if (
                not lnk_icon
                and lnk_data.extra
                and lnk_data.extra.icon_location_block
                and lnk_data.extra.icon_location_block.target_unicode
            ):
                icon_loc_extra = lnk_data.extra.icon_location_block.target_unicode
                expanded_path = os.path.expandvars(icon_loc_extra)
                lnk_icon = try_get_icon(expanded_path)
                if lnk_icon:
                    logging.debug(f"LNK icon found via extra block: {expanded_path}")

            if not lnk_icon and lnk_data.data:
                working_dir = lnk_data.data.working_directory
                relative = lnk_data.data.relative_path
                abs_path_cand = lnk_data.data.absolute_path

                if working_dir and relative:
                    try:
                        if os.path.isdir(working_dir):
                            target_path = os.path.normpath(
                                os.path.join(working_dir, relative)
                            )
                        else:
                            logging.debug(
                                f"Working directory '{working_dir}' for lnk '{full_path}' does not exist."
                            )
                    except Exception as join_err:
                        logging.warning(
                            f"Error joining path '{working_dir}' and '{relative}': {join_err}"
                        )
                elif abs_path_cand:
                    target_path = os.path.normpath(abs_path_cand)

        except (OSError, Exception) as parse_err:
            logging.error(
                f"Error reading or parsing .lnk file '{full_path}': {parse_err}"
            )
            return None

        if lnk_icon:
            return lnk_icon

        if target_path:
            target_icon = try_get_icon(target_path)
            if target_icon:
                logging.debug(f"LNK icon found via target path fallback: {target_path}")
                return target_icon
            else:
                logging.debug(
                    f"LNK target path ('{target_path}') did not yield a valid icon."
                )

        logging.debug(
            f"Could not determine icon from LNK location or target for '{full_path}'."
        )
        return None


class ThumbnailWorker(BaseIconWorker):
    """Generates thumbnail icons for image files."""

    def __init__(self, target_size: QSize):
        self.target_size = target_size

    def can_handle(self, path_info: Dict[str, Any]) -> bool:
        if path_info["path_type"] != "file":
            return False
        extension = path_info["extension"]
        return extension is not None and extension in SUPPORTED_IMAGE_EXTENSIONS

    def get_icon(self, path_info: Dict[str, Any]) -> Optional[QIcon]:
        if not self.can_handle(path_info):
            return None

        file_path = path_info["full_path"]
        logging.debug(f"ThumbnailWorker attempting to generate thumbnail for: {file_path}")
        try:
            reader = QImageReader(file_path)
            if not reader.canRead():
                logging.warning(
                    f"ThumbnailWorker: QImageReader cannot read file: {file_path}, Error: {reader.errorString()}"
                )
                return None

            reader.setAutoTransform(True)
            img = reader.read()
            if img.isNull():
                logging.warning(
                    f"ThumbnailWorker: QImageReader failed to read image data from: {file_path}, Error: {reader.errorString()}"
                )
                return None

            scaled_img = img.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            if scaled_img.isNull():
                logging.warning(f"ThumbnailWorker: Failed to scale image for: {file_path}")
                return None

            pixmap = QPixmap.fromImage(scaled_img)
            if not pixmap.isNull():
                logging.debug(f"ThumbnailWorker successfully generated thumbnail for: {file_path}")
                return QIcon(pixmap)
            else:
                logging.warning(
                    f"ThumbnailWorker: Failed to create QPixmap from scaled image for: {file_path}"
                )
                return None

        except Exception as e:
            logging.error(
                f"ThumbnailWorker: Error generating thumbnail for {file_path}: {e}",
                exc_info=True,
            )
            return None


def try_get_icon(path: Optional[str]) -> Optional[QIcon]:
    """Safely tries to create a QIcon from a path and checks if it's valid."""
    if isinstance(path, str) and path and os.path.exists(path):
        try:
            icon_candidate = QIcon(path)
            if not icon_candidate.isNull():
                logging.debug(f"Successfully loaded icon from: {path}")
                return icon_candidate
            else:
                logging.debug(f"QIcon is null for path: {path}")
        except Exception as e:
            logging.warning(f"Error creating QIcon for path '{path}': {e}")
    else:
        logging.debug(f"Icon path invalid or does not exist: {path}")
    return None

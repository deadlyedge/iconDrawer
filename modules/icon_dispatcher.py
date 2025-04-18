from abc import ABC, abstractmethod
import os
import sys
import logging
from typing import Any, Dict, Optional, TypedDict, Literal
from pydantic import BaseModel, Field, ValidationError

from PySide6.QtCore import QFileInfo, QSize, Qt
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import QFileIconProvider

try:
    import LnkParse3

    _HAS_LNKPARSE = True
except ImportError:
    logging.warning("LnkParse3 not found. .lnk file targets cannot be resolved.")
    _HAS_LNKPARSE = False

# Common image file extensions (case-insensitive)
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


# --- Merged from icon_validators.py ---

# Define a type hint for the validation result
PathType = Literal["file", "directory", "unknown"]


class ValidatedPathInfo(TypedDict):
    """Structure to hold information about a validated path."""

    full_path: str
    path_type: PathType
    extension: Optional[str]  # Lowercase extension for files, None otherwise


def validate_path(path: Optional[str]) -> Optional[ValidatedPathInfo]:
    """
    Validates a given path and returns structured information if valid.

    Args:
        path: The file system path to validate.

    Returns:
        A ValidatedPathInfo dictionary if the path is a valid string
        and exists, otherwise None.
    """
    if not isinstance(path, str) or not path:
        logging.debug(
            f"Validation failed: Path is not a valid string or is empty: {path}"
        )
        return None

    path_type: PathType = "unknown"
    extension: Optional[str] = None

    try:
        if os.path.isdir(path):
            path_type = "directory"
        elif os.path.isfile(path):
            path_type = "file"
            _, ext = os.path.splitext(path)
            extension = ext.lower()  # Store lowercase extension
        else:
            # Path exists but is neither file nor directory (e.g., broken symlink)
            # Or path does not exist
            logging.debug(
                f"Validation failed: Path does not exist or is not file/dir: {path}"
            )
            return (
                None  # Treat non-existent or non-file/dir as invalid for icon purposes
            )

    except OSError as e:
        # Handle potential OS errors during path checking (e.g., permission denied)
        logging.warning(f"Validation error for path '{path}': {e}")
        return None

    return {
        "full_path": path,
        "path_type": path_type,
        "extension": extension,
    }


# --- Original IconDispatcher class (unchanged) ---


class IconDispatcher:
    """Dispatches icon retrieval tasks to appropriate workers."""

    def __init__(self, icon_provider: DefaultIconProvider, thumbnail_size: QSize):
        """
        Initializes the dispatcher with an icon provider, thumbnail size,
        and worker instances.

        Args:
            icon_provider: An instance of DefaultIconProvider.
            thumbnail_size: The target QSize for thumbnails.
        """
        self.icon_provider = icon_provider
        self.directory_worker = DirectoryIconWorker()
        self.lnk_worker = LnkIconWorker()
        self.file_worker = FileIconWorker()
        # Pass thumbnail_size to ThumbnailWorker constructor
        self.thumbnail_worker = ThumbnailWorker(target_size=thumbnail_size)
        self._qt_icon_provider = QFileIconProvider()  # Instantiate QFileIconProvider
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

        logging.debug(
            f"Dispatching icon request for: {full_path} (Type: {path_type}, Ext: {extension})"
        )

        # --- Priority 1: Thumbnail (Files only) ---
        if path_type == "file":
            if self.thumbnail_worker.can_handle(path_info):
                logging.debug(f"Attempting ThumbnailWorker for: {full_path}")
                icon = self.thumbnail_worker.get_icon(path_info)
                if icon and not icon.isNull():
                    logging.debug(f"ThumbnailWorker succeeded for: {full_path}")
                    return icon
                else:
                    logging.debug(
                        f"ThumbnailWorker failed or returned null for: {full_path}"
                    )

        # --- Priority 2: LNK (Files only, Windows only) ---
        if (
            path_type == "file"
            and sys.platform == "win32"
            and extension == ".lnk"
            and _HAS_LNKPARSE
        ):
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
            logging.error(
                f"Error calling QFileIconProvider for '{full_path}': {e}", exc_info=True
            )

        # --- Priority 4: DirectoryWorker (Directories only) ---
        if path_type == "directory":
            logging.debug(f"Attempting DirectoryWorker for: {full_path}")
            icon = self.directory_worker.get_icon(path_info, self.icon_provider)
            if icon and not icon.isNull():
                logging.debug(f"DirectoryWorker succeeded for: {full_path}")
                return icon
            else:
                logging.debug(
                    f"DirectoryWorker failed or returned null for: {full_path}"
                )

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
                logging.debug(
                    f"FileWorker failed, returning generic file icon for: {full_path}"
                )
                return self.icon_provider.get_file_icon()  # Use generic file icon

        # --- Final Fallback ---
        # If it's not a file or directory, or all workers failed for a directory
        logging.warning(
            f"All icon retrieval methods failed for: {full_path}. Returning None."
        )
        return None  # Let icon_utils handle the final unknown icon


class BaseIconWorker(ABC):
    """Abstract base class for icon retrieval workers."""

    @abstractmethod
    def get_icon(
        self, path_info: ValidatedPathInfo, icon_provider: DefaultIconProvider
    ) -> Optional[QIcon]:
        """
        Attempts to retrieve an icon based on the validated path information.

        Args:
            path_info: Dictionary containing validated path details.
            icon_provider: An instance of DefaultIconProvider for accessing default icons.

        Returns:
            A QIcon object if successful, otherwise None.
        """
        pass


class DirectoryIconWorker(BaseIconWorker):
    """Worker responsible for providing the icon for directories."""

    def get_icon(
        self, path_info: ValidatedPathInfo, icon_provider: DefaultIconProvider
    ) -> Optional[QIcon]:
        """
        Returns the default folder icon.

        Args:
            path_info: Validated path information (not strictly needed here, but part of the interface).
            icon_provider: The provider for default icons.

        Returns:
            The default folder QIcon.
        """
        # For directories, we simply return the default folder icon
        return icon_provider.get_folder_icon()


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


# --- Pydantic Models for LnkParse3 JSON Structure ---
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


# --- End Pydantic Models ---


class LnkIconWorker(BaseIconWorker):
    """Worker responsible for extracting icons from .lnk shortcut files."""

    def get_icon(
        self, path_info: ValidatedPathInfo, icon_provider: DefaultIconProvider
    ) -> Optional[QIcon]:
        """
        Attempts to retrieve an icon from a .lnk file.

        Checks explicit icon locations within the .lnk structure first,
        then falls back to the icon of the target file/executable.

        Args:
            path_info: Validated path information for the .lnk file.
            icon_provider: The provider for default icons (used for fallback if needed by dispatcher).

        Returns:
            A QIcon object if found, otherwise None.
        """
        full_path = path_info["full_path"]

        # Ensure LnkParse3 is available and we are on Windows
        if not _HAS_LNKPARSE or sys.platform != "win32":
            logging.debug(
                "LnkParse3 not available or not on Windows, skipping LNK processing."
            )
            return None  # Let the dispatcher handle fallback

        lnk_icon: Optional[QIcon] = None
        target_path: Optional[str] = None

        try:
            with open(full_path, "rb") as infile:
                raw_json_data: Dict[str, Any] = LnkParse3.lnk_file(infile).get_json()

            # Validate the raw data using Pydantic
            try:
                lnk_data = LnkJsonModel.model_validate(raw_json_data)
            except ValidationError as val_err:
                logging.warning(
                    f"Validation failed for LnkParse3 data from '{full_path}': {val_err}"
                )
                lnk_data = LnkJsonModel()  # Use empty model on validation failure

            # 1. Try explicit icon location from 'data'
            if lnk_data.data and lnk_data.data.icon_location:
                lnk_icon = try_get_icon(lnk_data.data.icon_location)
                if lnk_icon:
                    logging.debug(
                        f"LNK icon found via data.icon_location: {lnk_data.data.icon_location}"
                    )

            # 2. Try explicit icon location from 'extra' block (expanding vars)
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

            # 3. Determine target path if no explicit icon found yet
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
            return None  # Error during parsing, fallback

        # 4. Return icon from explicit location if found
        if lnk_icon:
            return lnk_icon

        # 5. Try getting icon from the determined target path
        if target_path:
            target_icon = try_get_icon(target_path)
            if target_icon:
                logging.debug(f"LNK icon found via target path fallback: {target_path}")
                return target_icon
            else:
                logging.debug(
                    f"LNK target path ('{target_path}') did not yield a valid icon."
                )

        # 6. If no icon found from explicit location or target, return None
        logging.debug(
            f"Could not determine icon from LNK location or target for '{full_path}'."
        )
        return None


class ThumbnailWorker(BaseIconWorker):
    """
    Generates thumbnail icons for image files.
    """

    def __init__(self, target_size: QSize):
        """
        Initializes the worker with the target thumbnail size.

        Args:
            target_size: The QSize for the generated thumbnails.
        """
        self.target_size = target_size
        # QImageReader supports many formats out of the box

    def can_handle(self, path_info: ValidatedPathInfo) -> bool:
        """Checks if the path points to a supported image file."""
        # Access using dictionary keys
        if path_info["path_type"] != "file":
            return False
        # 'exists' check is implicitly done by validate_path returning non-None
        extension = path_info["extension"]
        return extension is not None and extension in SUPPORTED_IMAGE_EXTENSIONS

    def get_icon(self, path_info: ValidatedPathInfo) -> Optional[QIcon]:
        """Attempts to read the image and create a scaled thumbnail icon."""
        if not self.can_handle(path_info):
            # This check is technically redundant if dispatch logic calls can_handle first,
            # but good for robustness if worker is called directly.
            return None

        file_path = path_info["full_path"]  # Get the path using key
        logging.debug(
            f"ThumbnailWorker attempting to generate thumbnail for: {file_path}"
        )
        try:
            reader = QImageReader(file_path)
            if not reader.canRead():
                logging.warning(
                    f"ThumbnailWorker: QImageReader cannot read file: {file_path}, Error: {reader.errorString()}"
                )
                return None

            # Set a smaller target size for reading if possible (efficiency)
            # Consider device pixel ratio for high DPI displays later if needed
            reader.setAutoTransform(True)  # Apply EXIF orientation etc.

            # Read the image
            img = reader.read()
            if img.isNull():
                logging.warning(
                    f"ThumbnailWorker: QImageReader failed to read image data from: {file_path}, Error: {reader.errorString()}"
                )
                return None

            # Scale the image smoothly to fit the target size, keeping aspect ratio
            scaled_img = img.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            if scaled_img.isNull():
                logging.warning(
                    f"ThumbnailWorker: Failed to scale image for: {file_path}"
                )
                return None

            # Create QIcon from the scaled QPixmap
            pixmap = QPixmap.fromImage(scaled_img)
            if not pixmap.isNull():
                logging.debug(
                    f"ThumbnailWorker successfully generated thumbnail for: {file_path}"
                )
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
    """
    Safely tries to create a QIcon from a path and checks if it's valid.

    Args:
        path: The potential path to an icon file.

    Returns:
        A valid QIcon object if loading is successful, otherwise None.
    """
    if isinstance(path, str) and path and os.path.exists(path):
        try:
            icon_candidate = QIcon(path)
            # Check if the icon is not null (i.e., loading was successful)
            if not icon_candidate.isNull():
                logging.debug(f"Successfully loaded icon from: {path}")
                return icon_candidate
            else:
                logging.debug(f"QIcon is null for path: {path}")
        except Exception as e:
            logging.warning(f"Error creating QIcon for path '{path}': {e}")
            pass
    else:
        logging.debug(f"Icon path invalid or does not exist: {path}")
    return None

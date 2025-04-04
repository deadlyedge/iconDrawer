import os
import sys
from typing import Optional, Dict, Any
from PySide6.QtGui import QIcon  # Removed QPixmap as it's unused
import logging  # Import logging
from pydantic import BaseModel, Field, ValidationError, field_validator
from pathlib import Path  # Import Path for potential future use in models

# Import LnkParse3 safely
try:
    import LnkParse3

    _HAS_LNKPARSE = True
except ImportError:
    logging.warning("LnkParse3 not found. .lnk file targets cannot be resolved.")
    _HAS_LNKPARSE = False

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


def _initialize_default_icons():
    """Creates the default QIcon objects if they haven't been created yet."""
    global _DEFAULT_ICONS_INITIALIZED, DEFAULT_ICONS
    if _DEFAULT_ICONS_INITIALIZED:
        return

    # Default Folder Icon
    folder_icon_path = "asset/icons/folder_icon.png"  # Ensure asset path is correct
    if os.path.exists(folder_icon_path):
        DEFAULT_ICONS["folder"] = QIcon(folder_icon_path)
    else:
        logging.warning(
            f"Default folder icon not found at: {folder_icon_path}. Using fallback."
        )
        DEFAULT_ICONS["folder"] = QIcon.fromTheme(
            "folder", QIcon()
        )  # Fallback theme icon

    # Default Generic File Icon
    DEFAULT_ICONS["file"] = QIcon.fromTheme(
        "text-x-generic",
        QIcon(
            ":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png"
        ),  # Fallback resource
    )

    # Default Unknown Icon
    DEFAULT_ICONS["unknown"] = QIcon.fromTheme(
        "unknown",
        QIcon(
            ":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png"
        ),  # Fallback resource
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


def _try_get_icon(path: Optional[str]) -> Optional[QIcon]:
    """Safely tries to create a QIcon from a path and checks if it's valid."""
    if isinstance(path, str) and path and os.path.exists(path):
        try:
            icon_candidate = QIcon(path)
            if not icon_candidate.isNull():
                # print(f"[DEBUG Icon Loader] Success loading icon from: {path}")
                return icon_candidate
            # else:
            # print(f"[DEBUG Icon Loader] QIcon is null for path: {path}")
        except Exception as e:
            # Consider logging
            # print(f"Error creating QIcon for path '{path}': {e}")
            pass  # Add pass to fix indentation error
    # else:
    # print(f"[DEBUG Icon Loader] Path invalid or does not exist: {path}")
    return None


# --- Pydantic Models for LnkParse3 JSON Structure ---
# Define models only for the parts we actually use to keep it focused


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
    # Add other fields from LnkParse3's 'data' if needed later


class LnkJsonModel(BaseModel):
    data: Optional[LnkLinkData] = None
    extra: Optional[LnkExtraData] = None
    # Add other top-level fields from LnkParse3 if needed later


# --- End Pydantic Models ---


def get_icon_for_path(full_path: str) -> QIcon:
    """
    Gets the appropriate QIcon for a given file system path.
    Handles regular files, directories, and .lnk shortcuts using LnkParse3.
    Provides fallbacks using a unified default icon dictionary.
    """
    _initialize_default_icons()

    # Get default icons safely, providing a basic QIcon() if somehow still None
    unknown_icon = DEFAULT_ICONS.get("unknown") or QIcon()
    folder_icon = DEFAULT_ICONS.get("folder") or QIcon()
    generic_file_icon = DEFAULT_ICONS.get("file") or QIcon()  # Renamed from file_icon

    if not isinstance(full_path, str) or not full_path:
        return unknown_icon

    icon = unknown_icon  # Start with unknown

    if os.path.isdir(full_path):
        icon = folder_icon
    elif os.path.isfile(full_path):
        _, ext_lower = os.path.splitext(
            full_path.lower()
        )  # Use lowercase for matching, renamed ext

        # Special handling for .lnk files using LnkParse3 only
        if (
            sys.platform == "win32" and ext_lower == ".lnk" and _HAS_LNKPARSE
        ):  # Fixed: use ext_lower
            lnk_icon: Optional[QIcon] = None
            target_path: Optional[str] = (
                None  # Path to the actual target executable/file
            )

            try:
                with open(full_path, "rb") as infile:
                    raw_json_data: Dict[str, Any] = LnkParse3.lnk_file(
                        infile
                    ).get_json()

                # Validate the raw data using Pydantic
                try:
                    lnk_data = LnkJsonModel.model_validate(raw_json_data)
                except ValidationError as val_err:
                    logging.warning(
                        f"Validation failed for LnkParse3 data from '{full_path}': {val_err}"
                    )
                    lnk_data = LnkJsonModel()  # Use empty model on validation failure

                # Access data through the validated model
                if lnk_data.data:
                    # 1. Try explicit icon location first
                    if lnk_data.data.icon_location:
                        lnk_icon = _try_get_icon(lnk_data.data.icon_location)
                        # if lnk_icon: print(f"[DEBUG LNK] Icon found via data.icon_location: {lnk_data.data.icon_location}")

                # 2. If not found, try extra icon location block (expanding vars)
                if (
                    not lnk_icon
                    and lnk_data.extra
                    and lnk_data.extra.icon_location_block
                ):
                    if lnk_data.extra.icon_location_block.target_unicode:
                        icon_loc_extra = (
                            lnk_data.extra.icon_location_block.target_unicode
                        )
                        expanded_path = os.path.expandvars(icon_loc_extra)
                        lnk_icon = _try_get_icon(expanded_path)
                        # if lnk_icon: print(f"[DEBUG LNK] Icon found via extra block: {expanded_path}")

                # 3. If still no icon, determine target path for fallback
                if lnk_data.data:
                    working_dir = lnk_data.data.working_directory
                    relative = lnk_data.data.relative_path
                    abs_path_cand = lnk_data.data.absolute_path

                    if working_dir and relative:
                        try:
                            # Ensure working_dir exists before joining
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

            except (
                OSError,
                Exception,
            ) as parse_err:  # Catch file errors and LnkParse3 errors
                logging.error(
                    f"Error reading or parsing .lnk file '{full_path}': {parse_err}"
                )

            # 4. If we found an icon from location fields, use it
            if lnk_icon:
                icon = lnk_icon
            # 5. If no icon from location, try getting icon from target path
            elif target_path:
                target_icon = _try_get_icon(target_path)
                if target_icon:
                    icon = target_icon
                    # print(f"[DEBUG LNK] Icon found via target path fallback: {target_path}")
                else:
                    icon = generic_file_icon  # Use renamed variable
                    # print(f"[DEBUG LNK] Icon location and target path ('{target_path}') failed. Using default.")
            # 6. If no icon location and no valid target path, use default
            else:
                icon = generic_file_icon  # Use renamed variable
                # print(f"[DEBUG LNK] Could not determine icon location or target path for '{full_path}'. Using default.")

        else:
            # Standard file handling for non-lnk files or non-windows
            # 1. Check for specific default icon based on extension
            specific_icon = DEFAULT_ICONS.get(ext_lower)
            if specific_icon:
                icon = specific_icon
            else:
                # 2. Try loading icon directly from the file path using helper
                std_icon = _try_get_icon(full_path)
                if std_icon:
                    icon = std_icon
                else:
                    # 3. Fallback to generic file icon
                    icon = generic_file_icon

    return icon if icon else unknown_icon  # Final safety check

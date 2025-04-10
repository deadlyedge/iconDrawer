import os
import sys
import logging
from typing import Optional, Dict, Any
from PySide6.QtGui import QIcon
from pydantic import BaseModel, Field, ValidationError, field_validator

from .base_worker import BaseIconWorker
from ..icon_provider import DefaultIconProvider
from ..icon_validators import ValidatedPathInfo
from .utils import try_get_icon  # Import the helper function

# Import LnkParse3 safely
try:
    import LnkParse3

    _HAS_LNKPARSE = True
except ImportError:
    logging.warning("LnkParse3 not found. .lnk file targets cannot be resolved.")
    _HAS_LNKPARSE = False


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
                if lnk_icon: logging.debug(f"LNK icon found via data.icon_location: {lnk_data.data.icon_location}")

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
                if lnk_icon: logging.debug(f"LNK icon found via extra block: {expanded_path}")

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
            return None # Error during parsing, fallback

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
                logging.debug(f"LNK target path ('{target_path}') did not yield a valid icon.")

        # 6. If no icon found from explicit location or target, return None
        logging.debug(f"Could not determine icon from LNK location or target for '{full_path}'.")
        return None

import os
import sys
from typing import Optional
from PySide6.QtGui import QIcon, QPixmap

# Import LnkParse3 safely
try:
    import LnkParse3
    _HAS_LNKPARSE = True
except ImportError:
    print("Warning: LnkParse3 not found. .lnk file targets cannot be resolved.")
    _HAS_LNKPARSE = False

# Define default icons as None initially, create them lazily
DEFAULT_FILE_ICON: Optional[QIcon] = None
DEFAULT_FOLDER_ICON: Optional[QIcon] = None
DEFAULT_UNKNOWN_ICON: Optional[QIcon] = None

def _initialize_default_icons():
    """Creates the default QIcon objects if they haven't been created yet."""
    global DEFAULT_FILE_ICON, DEFAULT_FOLDER_ICON, DEFAULT_UNKNOWN_ICON
    if DEFAULT_FILE_ICON is None:
        DEFAULT_FILE_ICON = QIcon.fromTheme(
            "text-x-generic",
            QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png")
        )
    if DEFAULT_FOLDER_ICON is None:
        DEFAULT_FOLDER_ICON = QIcon("asset/folder_icon.png") # Ensure asset path is correct
    if DEFAULT_UNKNOWN_ICON is None:
        DEFAULT_UNKNOWN_ICON = QIcon.fromTheme(
            "unknown",
            QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png")
        )

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
            print(f"Error creating QIcon for path '{path}': {e}")
    # else:
        # print(f"[DEBUG Icon Loader] Path invalid or does not exist: {path}")
    return None

def get_icon_for_path(full_path: str) -> QIcon:
    """
    Gets the appropriate QIcon for a given file system path.
    Handles regular files, directories, and .lnk shortcuts using LnkParse3.
    """
    _initialize_default_icons()
    # Ensure defaults are not None before use
    unknown_icon = DEFAULT_UNKNOWN_ICON if DEFAULT_UNKNOWN_ICON else QIcon()
    folder_icon = DEFAULT_FOLDER_ICON if DEFAULT_FOLDER_ICON else QIcon()
    file_icon = DEFAULT_FILE_ICON if DEFAULT_FILE_ICON else QIcon()

    if not isinstance(full_path, str) or not full_path:
        return unknown_icon

    icon = unknown_icon # Start with unknown

    if os.path.isdir(full_path):
        icon = folder_icon
    elif os.path.isfile(full_path):
        _, ext = os.path.splitext(full_path)

        # Special handling for .lnk files using LnkParse3 only
        if sys.platform == 'win32' and ext.lower() == '.lnk' and _HAS_LNKPARSE:
            lnk_icon = None
            target_path = None # Path to the actual target executable/file
            try:
                with open(full_path, 'rb') as infile:
                    json_data = LnkParse3.lnk_file(infile).get_json()

                if isinstance(json_data, dict):
                    # 1. Try explicit icon location first
                    if 'data' in json_data and isinstance(json_data['data'], dict):
                        icon_loc = json_data['data'].get('icon_location')
                        lnk_icon = _try_get_icon(icon_loc)
                        if lnk_icon: print(f"[DEBUG LNK] Icon found via data.icon_location: {icon_loc}")

                    # 2. If not found, try extra icon location block (expanding vars)
                    if not lnk_icon and 'extra' in json_data and isinstance(json_data['extra'], dict):
                         icon_block = json_data['extra'].get('ICON_LOCATION_BLOCK')
                         if isinstance(icon_block, dict):
                             icon_loc_extra = icon_block.get('target_unicode')
                             if isinstance(icon_loc_extra, str) and icon_loc_extra:
                                 expanded_path = os.path.expandvars(icon_loc_extra)
                                 lnk_icon = _try_get_icon(expanded_path)
                                 if lnk_icon: print(f"[DEBUG LNK] Icon found via extra block: {expanded_path}")

                    # 3. If still no icon, determine target path for fallback
                    if 'data' in json_data and isinstance(json_data['data'], dict):
                        lnk_data = json_data['data']
                        working_dir = lnk_data.get('working_directory')
                        relative = lnk_data.get('relative_path')
                        abs_path_cand = lnk_data.get('absolute_path')

                        if isinstance(working_dir, str) and working_dir and isinstance(relative, str) and relative:
                            try:
                                target_path = os.path.normpath(os.path.join(working_dir, relative))
                            except Exception: pass # Ignore join errors
                        elif isinstance(abs_path_cand, str) and abs_path_cand:
                             target_path = os.path.normpath(abs_path_cand)

            except LnkParse3.errors.LnkParseError as parse_err:
                print(f"Error parsing .lnk file '{full_path}' with LnkParse3: {parse_err}")
            except Exception as e:
                print(f"Error processing .lnk file '{full_path}': {e}")

            # 4. If we found an icon from location fields, use it
            if lnk_icon:
                icon = lnk_icon
            # 5. If no icon from location, try getting icon from target path
            elif target_path:
                target_icon = _try_get_icon(target_path)
                if target_icon:
                    icon = target_icon
                    print(f"[DEBUG LNK] Icon found via target path fallback: {target_path}")
                else:
                    icon = file_icon # Fallback if target exists but icon is null
                    print(f"[DEBUG LNK] Icon location and target path ('{target_path}') failed. Using default.")
            # 6. If no icon location and no valid target path, use default
            else:
                icon = file_icon
                print(f"[DEBUG LNK] Could not determine icon location or target path for '{full_path}'. Using default.")

        else:
            # Standard file handling for non-lnk files or non-windows
            std_icon = QIcon(full_path)
            if not std_icon.isNull():
                icon = std_icon
            else:
                icon = file_icon # Fallback for standard files

    return icon if icon else unknown_icon # Final safety check

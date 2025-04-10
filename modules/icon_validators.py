import os
import logging # Import logging
from typing import Optional, TypedDict, Literal

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
        logging.debug(f"Validation failed: Path is not a valid string or is empty: {path}")
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
            logging.debug(f"Validation failed: Path does not exist or is not file/dir: {path}")
            return None  # Treat non-existent or non-file/dir as invalid for icon purposes

    except OSError as e:
        # Handle potential OS errors during path checking (e.g., permission denied)
        logging.warning(f"Validation error for path '{path}': {e}")
        return None

    return {
        "full_path": path,
        "path_type": path_type,
        "extension": extension,
    }

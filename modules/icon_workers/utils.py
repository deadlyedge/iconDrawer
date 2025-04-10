import os
import logging
from typing import Optional
from PySide6.QtGui import QIcon


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

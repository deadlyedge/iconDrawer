from typing import Optional
from PySide6.QtGui import QIcon
from .base_worker import BaseIconWorker
from ..icon_provider import DefaultIconProvider
from ..icon_validators import ValidatedPathInfo


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

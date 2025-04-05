from abc import ABC, abstractmethod
from typing import Optional
from PySide6.QtGui import QIcon
from ..icon_provider import DefaultIconProvider
from ..icon_validators import ValidatedPathInfo


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

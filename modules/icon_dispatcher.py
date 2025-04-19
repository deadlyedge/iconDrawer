import os
import sys
import logging
from typing import Optional, TypedDict, Literal
from PySide6.QtCore import QFileInfo, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider

from modules.icon_workers import (
    DirectoryIconWorker,
    FileIconWorker,
    LnkIconWorker,
    ThumbnailWorker,
    # BaseIconWorker,
)

try:
    import LnkParse3  # noqa: F401

    _HAS_LNKPARSE = True
except ImportError:
    logging.warning("LnkParse3 not found. .lnk file targets cannot be resolved.")
    _HAS_LNKPARSE = False


class DefaultIconProvider:
    """管理和提供默认图标的类，基于配置的路径和主题加载图标。"""

    def __init__(
        self,
        folder_icon_path: str,
        file_icon_theme: str,
        unknown_icon_theme: str,
        extension_icon_map: Optional[dict[str, str]] = None,
    ):
        self._icons: dict[str, QIcon] = {}
        self._load_default_icons(folder_icon_path, file_icon_theme, unknown_icon_theme)
        if extension_icon_map is not None:
            self._load_extension_icons(extension_icon_map)

    def _load_default_icons(
        self, folder_icon_path: str, file_icon_theme: str, unknown_icon_theme: str
    ):
        """加载默认文件夹、文件和未知图标，优先使用路径，其次使用主题图标。"""
        if os.path.exists(folder_icon_path):
            self._icons["folder"] = QIcon(folder_icon_path)
        else:
            logging.warning(
                f"默认文件夹图标路径无效，使用主题图标替代: {folder_icon_path}"
            )
            self._icons["folder"] = QIcon.fromTheme("folder", QIcon())

        self._icons["file"] = QIcon.fromTheme(file_icon_theme, QIcon())
        self._icons["unknown"] = QIcon.fromTheme(unknown_icon_theme, QIcon())

    def _load_extension_icons(self, extension_icon_map: dict[str, str]):
        """根据扩展名映射加载对应图标，路径优先，其次主题图标。"""
        for ext, icon_path_or_theme in extension_icon_map.items():
            if os.path.exists(icon_path_or_theme):
                icon = QIcon(icon_path_or_theme)
            else:
                icon = QIcon.fromTheme(icon_path_or_theme, QIcon())
            if not icon.isNull():
                self._icons[ext.lower()] = icon

    def get_icon(self, icon_type: str) -> QIcon:
        """获取指定类型的默认图标，找不到时返回未知图标。"""
        return self._icons.get(icon_type) or self.get_unknown_icon()

    def get_folder_icon(self) -> QIcon:
        """获取默认文件夹图标。"""
        return self._icons.get("folder") or self.get_unknown_icon()

    def get_file_icon(self) -> QIcon:
        """获取默认文件图标。"""
        return self._icons.get("file") or self.get_unknown_icon()

    def get_unknown_icon(self) -> QIcon:
        """获取默认未知图标。"""
        return self._icons.get("unknown") or QIcon()

    def get_icon_for_extension(self, extension: str) -> Optional[QIcon]:
        """根据文件扩展名获取对应的默认图标（忽略大小写）。"""
        return self._icons.get(extension.lower())


# 类型定义，表示路径类型
PathType = Literal["file", "directory", "unknown"]


class ValidatedPathInfo(TypedDict):
    full_path: str
    path_type: PathType
    extension: Optional[str]


def validate_path(path: Optional[str]) -> Optional[ValidatedPathInfo]:
    """验证路径是否存在并返回结构化信息，失败返回None。"""
    if not isinstance(path, str) or not path:
        logging.debug(f"路径无效或为空: {path}")
        return None

    try:
        if os.path.isdir(path):
            path_type = "directory"
            extension = None
        elif os.path.isfile(path):
            path_type = "file"
            _, ext = os.path.splitext(path)
            extension = ext.lower()
        else:
            logging.debug(f"路径不存在或非文件/目录: {path}")
            return None
    except OSError as e:
        logging.warning(f"路径验证异常: {path}, 错误: {e}")
        return None

    return {"full_path": path, "path_type": path_type, "extension": extension}


class IconDispatcher:
    """图标请求调度器，根据路径信息调用对应worker获取图标。"""

    def __init__(self, icon_provider: DefaultIconProvider, thumbnail_size: QSize):
        self.icon_provider = icon_provider
        self.directory_worker = DirectoryIconWorker()
        self.lnk_worker = LnkIconWorker()
        self.file_worker = FileIconWorker()
        self.thumbnail_worker = ThumbnailWorker(target_size=thumbnail_size)
        self._qt_icon_provider = QFileIconProvider()

    def dispatch(self, path_info: ValidatedPathInfo) -> Optional[QIcon]:
        full_path = path_info["full_path"]
        path_type = path_info["path_type"]
        extension = path_info["extension"]
        icon: Optional[QIcon] = None

        logging.debug(
            f"Dispatching icon request for: {full_path} (Type: {path_type}, Ext: {extension})"
        )

        # 新增：优先根据扩展名映射返回图标
        if path_type == "file" and extension:
            ext_icon = self.icon_provider.get_icon_for_extension(extension)
            if ext_icon is not None and not ext_icon.isNull():
                logging.debug(f"Extension icon found for {extension} at {full_path}")
                return ext_icon

        if path_type == "file":
            if self.thumbnail_worker.can_handle(dict(path_info)):
                logging.debug(f"Attempting ThumbnailWorker for: {full_path}")
                icon = self.thumbnail_worker.get_icon(dict(path_info))
                if icon and not icon.isNull():
                    logging.debug(f"ThumbnailWorker succeeded for: {full_path}")
                    return icon
                else:
                    logging.debug(
                        f"ThumbnailWorker failed or returned null for: {full_path}"
                    )

        if (
            path_type == "file"
            and sys.platform == "win32"
            and extension == ".lnk"
            and _HAS_LNKPARSE
        ):
            logging.debug(f"Attempting LnkWorker for: {full_path}")
            icon = self.lnk_worker.get_icon(dict(path_info), self.icon_provider)
            if icon and not icon.isNull():
                logging.debug(f"LnkWorker succeeded for: {full_path}")
                return icon
            else:
                logging.debug(f"LnkWorker failed or returned null for: {full_path}")

        try:
            logging.debug(f"Attempting QFileIconProvider for: {full_path}")
            file_info = QFileInfo(full_path)
            qt_icon = self._qt_icon_provider.icon(file_info)
            if not qt_icon.isNull():
                logging.debug(f"QFileIconProvider succeeded for: {full_path}")
                return qt_icon
            else:
                logging.debug(f"QFileIconProvider returned null icon for: {full_path}")
        except Exception as e:
            logging.error(
                f"Error calling QFileIconProvider for '{full_path}': {e}", exc_info=True
            )

        if path_type == "directory":
            logging.debug(f"Attempting DirectoryWorker for: {full_path}")
            icon = self.directory_worker.get_icon(dict(path_info), self.icon_provider)
            if icon and not icon.isNull():
                logging.debug(f"DirectoryWorker succeeded for: {full_path}")
                return icon
            else:
                logging.debug(
                    f"DirectoryWorker failed or returned null for: {full_path}"
                )

        if path_type == "file":
            logging.debug(f"Attempting FileWorker as fallback for: {full_path}")
            icon = self.file_worker.get_icon(dict(path_info), self.icon_provider)
            if icon and not icon.isNull():
                logging.debug(f"FileWorker succeeded for: {full_path}")
                return icon
            else:
                logging.debug(
                    f"FileWorker failed, returning generic file icon for: {full_path}"
                )
                return self.icon_provider.get_file_icon()

        logging.warning(
            f"All icon retrieval methods failed for: {full_path}. Returning None."
        )
        return None

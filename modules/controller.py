import logging
from typing import List, Optional, TYPE_CHECKING, Tuple
from PySide6.QtCore import QObject, QPoint, QSize, Slot, Signal
from PySide6.QtWidgets import QListWidgetItem, QMessageBox
from modules.settings_manager import SettingsManager, DrawerDict
from pathlib import Path

from modules.icon_loader import _initialize_icon_components, _icon_provider
from modules.icon_dispatcher import DefaultIconProvider
from modules.drawer_data_manager import DataManager, FileInfo

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if TYPE_CHECKING:
    from modules.main_window import MainWindow

USER_ROLE: int = 32  # Qt.ItemDataRole.UserRole starts at 32


class AppController(QObject):
    """
    应用控制器，管理状态和逻辑，协调视图(MainWindow)与数据(SettingsManager)。
    """

    showDrawerContent = Signal(dict, QSize)
    hideDrawerContent = Signal()
    updateDrawerContent = Signal(str)

    def __init__(
        self, main_view: "MainWindow", parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._main_view = main_view
        self.settings_manager = SettingsManager()
        self._drawers_data: List[DrawerDict] = []
        self._window_position: Optional[QPoint] = None
        self._background_color_hsla: Tuple[int, int, int, float] = (
            self.settings_manager.DEFAULT_BG_COLOR_HSLA
        )
        self._start_with_windows: bool = (
            self.settings_manager.DEFAULT_START_WITH_WINDOWS
        )
        self._default_icon_folder_path: str = (
            self.settings_manager.DEFAULT_ICON_FOLDER_PATH
        )
        self._default_icon_file_theme: str = (
            self.settings_manager.DEFAULT_ICON_FILE_THEME
        )
        self._default_icon_unknown_theme: str = (
            self.settings_manager.DEFAULT_ICON_UNKNOWN_THEME
        )
        self._thumbnail_size: QSize = QSize(
            self.settings_manager.DEFAULT_THUMBNAIL_SIZE.width,
            self.settings_manager.DEFAULT_THUMBNAIL_SIZE.height,
        )
        self._locked: bool = False
        self._locked_item_data: Optional[DrawerDict] = None
        self._extension_icon_map: dict[str, str] = {}

        self.icon_provider: Optional[DefaultIconProvider] = None
        self.drawer_data_manager = DataManager()
        self.drawer_data_manager.directoryChanged.connect(self.on_directory_changed)

        _initialize_icon_components()
        self.icon_provider = _icon_provider
        if not self.icon_provider:
            logging.critical("Icon provider failed to initialize in controller!")

        self._load_initial_data()

    def _load_initial_data(self) -> None:
        """加载初始设置并更新视图。"""
        (
            drawers,
            window_pos,
            bg_color,
            start_flag,
            icon_folder_path,
            icon_file_theme,
            icon_unknown_theme,
            thumbnail_qsize,
            extension_icon_map,
        ) = self.settings_manager.load_settings()

        self._drawers_data = drawers
        self._window_position = window_pos
        self._background_color_hsla = bg_color
        self._start_with_windows = start_flag
        self._default_icon_folder_path = icon_folder_path
        self._default_icon_file_theme = icon_file_theme
        self._default_icon_unknown_theme = icon_unknown_theme
        self._thumbnail_size = thumbnail_qsize
        self._extension_icon_map = extension_icon_map or {}

        self._main_view.populate_drawer_list(self._drawers_data)
        if self._window_position:
            self._main_view.set_initial_position(self._window_position)

        # 新增：启动监控并预加载所有抽屉内容
        paths = [d["path"] for d in self._drawers_data if "path" in d]
        if paths:
            self.drawer_data_manager.start_monitor(paths)
            for p in paths:
                self.drawer_data_manager.reload_drawer_content(p)

    def save_settings(self) -> None:
        """保存当前状态（抽屉列表和窗口位置）。"""
        current_pos = self._main_view.get_current_position()
        if current_pos:
            self._window_position = current_pos

        self.settings_manager.save_settings(
            drawers=self._drawers_data,
            window_position=self._window_position,
            background_color_hsla=self._background_color_hsla,
            start_with_windows=self._start_with_windows,
            default_icon_folder_path=self._default_icon_folder_path,
            default_icon_file_theme=self._default_icon_file_theme,
            default_icon_unknown_theme=self._default_icon_unknown_theme,
            thumbnail_size=self._thumbnail_size,
            extension_icon_map=self._extension_icon_map,
        )

    def add_new_drawer(self) -> None:
        """添加新抽屉。"""
        folder_path_str = self._main_view.prompt_for_folder()
        if not folder_path_str:
            return

        folder_path = Path(folder_path_str)
        if not folder_path.is_dir():
            logging.error(f"Selected path is not a valid directory: {folder_path_str}")
            QMessageBox.warning(
                self._main_view,
                "无效路径",
                f"选择的路径不是一个有效的文件夹:\n{folder_path_str}",
            )
            return

        if any(d.get("path") == folder_path_str for d in self._drawers_data):
            QMessageBox.warning(
                self._main_view,
                "重复抽屉",
                f"路径 '{folder_path_str}' 已经被添加。",
            )
            return

        new_drawer_data: DrawerDict = {
            "name": folder_path.name,
            "path": folder_path_str,
        }
        self._drawers_data.append(new_drawer_data)
        self._main_view.add_drawer_item(new_drawer_data)
        self.save_settings()
        self.drawer_data_manager.reload_drawer_content(folder_path_str)

    def update_drawer_size(self, drawer_name: str, new_size: QSize) -> None:
        """更新指定抽屉的尺寸信息。"""
        for drawer in self._drawers_data:
            if drawer.get("name") == drawer_name:
                if drawer.get("size") != new_size:
                    drawer["size"] = new_size
                    self.save_settings()
                break

    def update_window_position(self, pos: QPoint) -> None:
        """更新窗口位置（仅内存）。"""
        if self._window_position != pos:
            self._window_position = pos

    def get_preloaded_file_list(self, drawer_path: str) -> Optional[List[FileInfo]]:
        """通过 DataManager 获取预加载文件列表。"""
        self._last_requested_folder = drawer_path
        return self.drawer_data_manager.get_file_list(drawer_path)

    def on_directory_changed(self, path: str) -> None:
        """目录变动时刷新内容。"""
        self.updateDrawerContent.emit(path)

    def handle_item_selected(self, item: QListWidgetItem) -> None:
        """处理抽屉列表项选中及锁定逻辑。"""
        drawer_data = item.data(USER_ROLE)
        if not isinstance(drawer_data, dict):
            logging.error(f"Invalid data in selected item '{item.text()}'.")
            return

        folder_path_str = drawer_data.get("path")
        if not folder_path_str or not Path(folder_path_str).is_dir():
            logging.error(
                f"Invalid or non-existent path for item '{item.text()}': {folder_path_str}"
            )
            QMessageBox.warning(
                self._main_view,
                "路径无效",
                f"抽屉 '{item.text()}' 的路径无效或不存在:\n{folder_path_str}\n请考虑移除此抽屉。",
            )
            return

        current_drawer_config = None
        drawer_name_to_find = drawer_data.get("name")
        if drawer_name_to_find:
            for config in self._drawers_data:
                if config.get("name") == drawer_name_to_find:
                    current_drawer_config = config
                    break

        if current_drawer_config:
            target_content_size = current_drawer_config.get("size")
            if not isinstance(target_content_size, QSize):
                target_content_size = QSize(640, 480)
            item.setData(USER_ROLE, current_drawer_config)
        else:
            logging.warning(
                f"Could not find '{drawer_name_to_find}' in current config, using item data size."
            )
            target_content_size = drawer_data.get("size")
            if not isinstance(target_content_size, QSize):
                target_content_size = QSize(640, 480)

        if self._locked:
            compare_data = (
                current_drawer_config if current_drawer_config else drawer_data
            )
            if compare_data == self._locked_item_data:
                self._locked = False
                self._locked_item_data = None
                self.hideDrawerContent.emit()
            else:
                if self._locked_item_data:
                    old_drawer_name = self._locked_item_data.get("name")
                    if old_drawer_name:
                        old_size = self._main_view.get_drawer_content_size()
                        self.update_drawer_size(old_drawer_name, old_size)
                self._locked_item_data = compare_data
                self.showDrawerContent.emit(self._locked_item_data, target_content_size)
        else:
            self._locked = True
            self._locked_item_data = (
                current_drawer_config if current_drawer_config else drawer_data
            )
            self.showDrawerContent.emit(self._locked_item_data, target_content_size)

    def handle_selection_cleared(self) -> None:
        """列表选择清除时隐藏内容（若未锁定）。"""
        if not self._locked:
            self.hideDrawerContent.emit()

    def handle_content_close_requested(self) -> None:
        """内容关闭请求处理，保存尺寸并隐藏内容。"""
        if self._locked and self._locked_item_data:
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                current_size = self._main_view.get_drawer_content_size()
                self.update_drawer_size(drawer_name, current_size)

        self._locked = False
        self._locked_item_data = None
        self.hideDrawerContent.emit()
        self._main_view.clear_list_selection()

    def handle_content_resize_finished(self) -> None:
        """内容尺寸调整完成时保存尺寸。"""
        if self._locked and self._locked_item_data:
            current_size = self._main_view.get_drawer_content_size()
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                self.update_drawer_size(drawer_name, current_size)

    def handle_window_drag_finished(self) -> None:
        """窗口拖动完成时保存位置和尺寸。"""
        current_pos = self._main_view.get_current_position()
        if current_pos and self._window_position != current_pos:
            self._window_position = current_pos

        if self._locked and self._locked_item_data:
            current_size = self._main_view.get_drawer_content_size()
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                for drawer in self._drawers_data:
                    # Ensure drawer has a "size" key before comparing
                    if drawer.get("name") == drawer_name:
                        if (
                            not isinstance(drawer.get("size"), QSize)
                            or drawer.get("size") != current_size
                        ):
                            drawer["size"] = current_size
                        break

        self.save_settings()

    def handle_settings_requested(self) -> None:
        """打开设置对话框。"""
        self._main_view.show_settings_dialog()

    @Slot(float, float, float, float)
    def handle_background_applied(
        self, h_float: float, s_float: float, l_float: float, a_float: float
    ) -> None:
        """处理设置对话框应用的背景色（0-1浮点数）。"""
        new_color_css = (
            round(h_float * 359),
            round(s_float * 100),
            round(l_float * 100),
            a_float,
        )
        if self._background_color_hsla != new_color_css:
            self._background_color_hsla = new_color_css
            self.save_settings()
            logging.info(f"Background color updated to (CSS format): {new_color_css}")

    @Slot(bool)
    def handle_startup_toggled(self, enabled: bool) -> None:
        """处理启动项开关。"""
        if self._start_with_windows != enabled:
            self._start_with_windows = enabled
            self.save_settings()
            logging.info(f"Start with Windows setting updated to: {enabled}")
            self._update_startup_registry(enabled)

    def _update_startup_registry(self, enable: bool) -> None:
        """平台相关启动项逻辑占位符。"""
        if enable:
            logging.info("Placeholder: Adding application to system startup.")
        else:
            logging.info("Placeholder: Removing application from system startup.")

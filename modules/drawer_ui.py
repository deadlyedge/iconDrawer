import os
import shutil
import logging
from typing import Optional, Callable, TYPE_CHECKING, List

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QMessageBox,
    QHBoxLayout,
    QPushButton,
)
from PySide6.QtGui import (
    QIcon,
    QDesktopServices,
    QFontMetrics,
    QResizeEvent,
    QMouseEvent,
    QPaintEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QDragLeaveEvent,
)
from PySide6.QtCore import Qt, QSize, QUrl, Signal, QThreadPool

from .drawer_custom_size_grip import CustomSizeGrip
from .utils import calculate_available_label_width
from .file_item import FileIconWidget

if TYPE_CHECKING:
    from .controller import AppController, FileInfo


class ClickableWidget(QWidget):
    """可点击容器，支持设置点击回调。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.click_callback: Optional[Callable[[], None]] = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.click_callback:
            self.click_callback()
            event.accept()
        else:
            super().mousePressEvent(event)


class DrawerContentWidget(QWidget):
    """抽屉内容部件，用于展示文件夹内容和文件项"""

    closeRequested = Signal()
    sizeChanged = Signal(QSize)
    resizeFinished = Signal()

    def __init__(
        self, controller: "AppController", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setAcceptDrops(True)
        self.current_folder = ""
        self.icon_size = QSize(96, 96)
        self.item_size = (100, 120)
        self.items: List[FileIconWidget] = []
        self.icon_load_pool = QThreadPool()
        self.placeholder_folder_icon: Optional[QIcon] = None
        self.placeholder_file_icon: Optional[QIcon] = None

        self.folder_label: Optional[QLabel] = None
        self.folder_icon_label: Optional[QLabel] = None
        self.refresh_button: Optional[QPushButton] = None
        self.close_button: Optional[QPushButton] = None
        self.header_layout: Optional[QHBoxLayout] = None
        self.main_visual_container: Optional[QWidget] = None
        self.folder_container: Optional[ClickableWidget] = None
        self.scroll_area: Optional[QScrollArea] = None
        self.scroll_widget: Optional[QWidget] = None
        self.grid_layout: Optional[QGridLayout] = None
        self.size_grip: Optional[CustomSizeGrip] = None

        self._init_main_container()
        self._load_placeholder_icons()

    def _load_placeholder_icons(self) -> None:
        if self.controller and self.controller.icon_provider:
            self.placeholder_folder_icon = (
                self.controller.icon_provider.get_folder_icon()
            )
            self.placeholder_file_icon = self.controller.icon_provider.get_file_icon()
        else:
            logging.warning(
                "Icon provider not available, using empty icons as fallback."
            )
            self.placeholder_folder_icon = QIcon()
            self.placeholder_file_icon = QIcon()

    def _init_main_container(self) -> None:
        self.main_visual_container = QWidget(self)
        self.main_visual_container.setObjectName("drawerContentContainer")
        self.main_visual_container.setProperty("isDrawerContentContainer", True)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_visual_container)

        container_layout = QGridLayout(self.main_visual_container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        container_layout.setSpacing(0)

        header_layout = self._create_header()
        container_layout.addLayout(header_layout, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(5)
        self.scroll_area.setWidget(self.scroll_widget)

        container_layout.addWidget(self.scroll_area, 1, 0)

        self.size_grip = CustomSizeGrip(self.main_visual_container)
        self.size_grip.setObjectName("sizeGrip")
        self.size_grip.resizeFinished.connect(self.resizeFinished.emit)
        container_layout.addWidget(
            self.size_grip,
            2,
            0,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )

    def _create_header(self) -> QHBoxLayout:
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(5, 2, 5, 2)

        self.folder_container = ClickableWidget(self)
        self.folder_container.setProperty("isFolderPathLayout", True)
        self.folder_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        folder_layout = QHBoxLayout(self.folder_container)
        folder_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_icon_label = QLabel(self.folder_container)
        self.folder_icon_label.setObjectName("folderIconLabel")
        folder_icon = QIcon()
        if self.controller and self.controller.icon_provider:
            folder_icon = self.controller.icon_provider.get_folder_icon()
        else:
            logging.error("Icon provider not available, using empty folder icon.")
        self.folder_icon_label.setPixmap(folder_icon.pixmap(16))
        folder_layout.addWidget(self.folder_icon_label)

        self.folder_label = QLabel("", self.folder_container)
        self.folder_label.setObjectName("folderLabel")
        folder_layout.addWidget(self.folder_label, 1, Qt.AlignmentFlag.AlignLeft)

        self.folder_container.click_callback = self.open_current_folder
        self.header_layout.addWidget(self.folder_container, 1)

        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setToolTip("刷新当前文件夹内容")
        self.refresh_button.clicked.connect(self._refresh_content)
        self.header_layout.addWidget(self.refresh_button, 0)

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("closeButton")
        self.close_button.setToolTip("关闭抽屉")
        self.close_button.clicked.connect(self.closeRequested.emit)
        self.header_layout.addWidget(self.close_button, 0)

        return self.header_layout

    def update_content(self, path: str) -> None:
        file_list = None
        if self.controller:
            self.controller.drawer_data_manager.reload_drawer_content(path)
            file_list = self.controller.get_preloaded_file_list(path)
        self.update_with_file_list(path, file_list)

    def update_with_file_list(
        self, folder_path: str, file_list: Optional[List]
    ) -> None:
        self.current_folder = folder_path
        if self.folder_label:
            self.folder_label.setText(folder_path)
            self.folder_label.setToolTip(f"click to open: {folder_path}")

        self.clear_grid()
        self.items.clear()

        if file_list is None:
            logging.info(f"文件列表为空，显示加载中: {folder_path}")
            loading_label = QLabel("正在加载...")
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self.grid_layout:
                self.grid_layout.addWidget(loading_label, 0, 0)
            return

        if not file_list:
            logging.debug(f"文件列表为空或目录为空: {folder_path}")
            self._update_folder_label_elided_text()
            return

        try:
            for file_info in file_list:
                placeholder_icon = (
                    self.placeholder_folder_icon
                    if file_info.is_dir
                    else self.placeholder_file_icon
                )
                if not placeholder_icon:
                    placeholder_icon = QIcon()
                container_widget = self._create_file_item_placeholder(
                    file_info, placeholder_icon
                )
                self.items.append(container_widget)

            self.relayout_grid()
            self._update_folder_label_elided_text()
            self._start_async_icon_loading()

        except Exception as e:
            logging.error(f"Error creating file items for {folder_path}: {e}")
            QMessageBox.critical(self, "错误", f"创建文件项时出错: {e!s}")

        self.update()

    def _start_async_icon_loading(self) -> None:
        if not self.items:
            return
        logging.debug(
            f"Starting async icon load for {len(self.items)} items in {self.current_folder}"
        )
        for item_widget in self.items:
            if isinstance(item_widget, FileIconWidget):
                placeholder_icon = (
                    self.placeholder_folder_icon
                    if item_widget.is_dir
                    else self.placeholder_file_icon
                )
                if placeholder_icon is None:
                    placeholder_icon = QIcon()
                item_widget.load_icon(placeholder_icon, self.icon_size)

    def _refresh_content(self) -> None:
        if self.current_folder and self.controller:
            logging.info(f"Force refreshing content for: {self.current_folder}")
            try:
                new_file_list = (
                    self.controller.drawer_data_manager.reload_drawer_content(
                        self.current_folder
                    )
                )
                self.update_with_file_list(self.current_folder, new_file_list)
                logging.info(f"Force refresh complete for: {self.current_folder}")
            except Exception as e:
                logging.error(
                    f"Error during force refresh for {self.current_folder}: {e}"
                )
                QMessageBox.warning(self, "刷新错误", f"刷新文件夹时出错:\n{e!s}")
        elif not self.current_folder:
            logging.warning("Cannot refresh, current_folder is not set.")
        elif not self.controller:
            logging.error("Cannot refresh, controller is not available.")

    def open_current_folder(self) -> None:
        if os.path.isdir(self.current_folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_folder))

    def _create_file_item_placeholder(
        self, file_info: "FileInfo", placeholder_icon: QIcon
    ) -> FileIconWidget:
        container_widget = FileIconWidget(file_info.path, file_info.is_dir)
        container_widget.setFixedSize(self.item_size[0], self.item_size[1])
        container_widget.load_icon(placeholder_icon, self.icon_size)
        text_available_width = self.item_size[0] - 10
        container_widget.set_text(file_info.name, text_available_width)
        return container_widget

    def relayout_grid(self) -> None:
        if not self.grid_layout:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        if not self.items:
            return

        if not self.scroll_area or not self.scroll_area.viewport():
            return
        viewport_width = self.scroll_area.viewport().width()
        available_width = (
            viewport_width
            if viewport_width > 0
            else (self.scroll_widget.width() if self.scroll_widget else self.width())
        )
        if available_width <= 0:
            available_width = self.item_size[0] * 3

        item_total_width = self.item_size[0] + self.grid_layout.horizontalSpacing()
        if item_total_width <= 0:
            item_total_width = self.item_size[0]

        columns = max(1, int(available_width // item_total_width))

        row, col = 0, 0
        for item_widget in self.items:
            self.grid_layout.addWidget(item_widget, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

        rows_needed = (len(self.items) + columns - 1) // columns
        min_height = rows_needed * (
            self.item_size[1] + self.grid_layout.verticalSpacing()
        )
        min_height += self.grid_layout.verticalSpacing()

        if self.scroll_widget:
            self.scroll_widget.setMinimumHeight(min_height)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.relayout_grid()
        self._update_folder_label_elided_text()
        self.sizeChanged.emit(event.size())

    def clear_grid(self) -> None:
        if not self.grid_layout:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

    def _update_folder_label_elided_text(self) -> None:
        if not all(
            [
                self.current_folder,
                self.folder_label,
                self.header_layout,
                self.folder_icon_label,
                self.refresh_button,
                self.close_button,
            ]
        ):
            return
        try:
            # Use assert to help type checker know these are not None
            assert self.header_layout is not None
            assert self.folder_icon_label is not None
            assert self.refresh_button is not None
            assert self.close_button is not None
            assert self.folder_label is not None

            available_width = calculate_available_label_width(
                self,
                self.header_layout,
                self.folder_icon_label,
                self.refresh_button,
                self.close_button,
            )
            fm = QFontMetrics(self.folder_label.font())
            elided_text = fm.elidedText(
                self.current_folder, Qt.TextElideMode.ElideLeft, available_width
            )
            self.folder_label.setText(elided_text)
            self.folder_label.setToolTip(f"click to open: {self.current_folder}")
        except Exception as e:
            logging.error(f"Error updating folder label text: {e}")
            if self.folder_label:
                self.folder_label.setText("...")
                self.folder_label.setToolTip(self.current_folder)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls() and self.scroll_area:
            if self.scroll_area.geometry().contains(event.pos()):
                self.scroll_area.setStyleSheet("border: 2px solid orange;")
            else:
                self.scroll_area.setStyleSheet("")
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        if self.scroll_area:
            self.scroll_area.setStyleSheet("")
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        if self.scroll_area:
            self.scroll_area.setStyleSheet("")
        if event.mimeData().hasUrls() and self.current_folder:
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    src_drive = os.path.splitdrive(file_path)[0].upper()
                    dest_drive = os.path.splitdrive(self.current_folder)[0].upper()
                    dest_path = os.path.join(
                        self.current_folder, os.path.basename(file_path)
                    )
                    try:
                        if src_drive == dest_drive:
                            shutil.move(file_path, dest_path)
                        else:
                            shutil.copy2(file_path, dest_path)
                    except Exception as e:
                        logging.error(f"Error transferring file {file_path}: {e}")
            self.update_content(self.current_folder)
            event.acceptProposedAction()
        else:
            event.ignore()

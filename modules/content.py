import os
import shutil
import logging
from typing import (
    Optional,
    Callable,
    TYPE_CHECKING,
    List,
)

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
from PySide6.QtCore import (
    Qt,
    QSize,
    QUrl,
    Signal,
    QThreadPool,
    Slot,
)

from .custom_size_grip import CustomSizeGrip
from .content_utils import calculate_available_label_width, truncate_text

# 引入拆分后的异步加载和文件项模块
from .icon_loader import IconWorkerSignals, IconLoadWorker
from .file_item import FileIconWidget

# Forward declare AppController 和 FileInfo
if TYPE_CHECKING:
    from .controller import AppController, FileInfo


class ClickableWidget(QWidget):
    """
    可点击容器，支持设置点击回调。
    """

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
    """
    抽屉内容部件，用于展示文件夹内容和文件项
    """

    closeRequested = Signal()
    sizeChanged = Signal(QSize)
    resizeFinished = Signal()

    def resize(self, size: QSize) -> None:
        super().resize(size)

    def move(self, x: int, y: int) -> None:
        super().move(x, y)

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)

    def setObjectName(self, name: str) -> None:
        super().setObjectName(name)

    def setMinimumSize(self, w: int, h: int) -> None:
        super().setMinimumSize(w, h)

    # Modify __init__ to accept the controller
    def __init__(
        self, controller: "AppController", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.controller = controller  # Store controller reference
        self.setAcceptDrops(True)
        self.current_folder = ""
        # Initialize first
        self.icon_size = QSize(96, 96)  # Restore original icon size
        self.item_size = (100, 120)  # Restore original item size
        self.items: List[FileIconWidget] = []  # Type hint items
        self.icon_load_pool = QThreadPool()  # Thread pool for icon loading
        self.placeholder_folder_icon: Optional[QIcon] = None
        self.placeholder_file_icon: Optional[QIcon] = None

        # Explicitly initialize UI elements to None before creation
        self.folder_label: Optional[QLabel] = None
        self.folder_icon_label: Optional[QLabel] = None
        self.refresh_button: Optional[QPushButton] = None  # Add refresh_button
        self.close_button: Optional[QPushButton] = None
        self.header_layout: Optional[QHBoxLayout] = None
        self.main_visual_container: Optional[QWidget] = None
        self.folder_container: Optional[ClickableWidget] = None
        self.scroll_area: Optional[QScrollArea] = None
        self.scroll_widget: Optional[QWidget] = None
        self.grid_layout: Optional[QGridLayout] = None
        self.size_grip: Optional[CustomSizeGrip] = None

        # self.available_label_width = 200 # Removed: No longer storing stale width

        # Now create the UI elements
        self._init_main_container()
        self._load_placeholder_icons()  # Load placeholders after controller is set

    def _load_placeholder_icons(self):
        """Load placeholder icons using the controller's provider."""
        if self.controller and self.controller.icon_provider:
            self.placeholder_folder_icon = (
                self.controller.icon_provider.get_folder_icon()
            )
            self.placeholder_file_icon = self.controller.icon_provider.get_file_icon()
            # Add fallback for unknown?
        else:
            logging.warning(
                "Icon provider not available, cannot load placeholder icons."
            )
            # Use default QIcons or load from file as fallback?
            self.placeholder_folder_icon = QIcon()
            self.placeholder_file_icon = QIcon()

    def _init_main_container(self) -> None:
        """
        初始化主视觉容器，包括头部、滚动区域和大小调整手柄
        """
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

        # container_layout.setRowStretch(0, 0)
        # container_layout.setRowStretch(1, 1)
        # container_layout.setRowStretch(2, 0)
        # container_layout.setColumnStretch(0, 1)

    def _create_header(self) -> QHBoxLayout:
        """
        创建头部布局，包含文件夹路径显示和关闭按钮
        """
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(5, 2, 5, 2)

        # Restore ClickableWidget as folder_container
        self.folder_container = ClickableWidget(self)
        self.folder_container.setProperty("isFolderPathLayout", True)
        self.folder_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )  # Container expands
        folder_layout = QHBoxLayout(self.folder_container)
        folder_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_icon_label = QLabel(self.folder_container)
        self.folder_icon_label.setObjectName("folderIconLabel")
        # Use icon_provider via controller to get the folder icon, with fallback
        folder_icon = QIcon()  # Default empty icon
        if self.controller and self.controller.icon_provider:
            folder_icon = self.controller.icon_provider.get_folder_icon()
        else:
            logging.error(
                "Icon provider not available in DrawerContentWidget, using empty icon for folder."
            )
        self.folder_icon_label.setPixmap(folder_icon.pixmap(16))  # Use 16px size
        folder_layout.addWidget(self.folder_icon_label)  # Add to inner layout

        self.folder_label = QLabel(
            "", self.folder_container
        )  # Initialize with empty string
        self.folder_label.setObjectName("folderLabel")
        # Use default size policy for label, let container handle expansion
        folder_layout.addWidget(
            self.folder_label, 1, Qt.AlignmentFlag.AlignLeft
        )  # Add to inner layout with stretch

        self.folder_container.click_callback = self.open_current_folder
        self.header_layout.addWidget(
            self.folder_container, 1
        )  # Add container with stretch

        # Add Refresh Button
        self.refresh_button = QPushButton("🔄")  # Or use an icon
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setToolTip("刷新当前文件夹内容")
        self.refresh_button.clicked.connect(self._refresh_content)
        self.header_layout.addWidget(
            self.refresh_button, 0
        )  # Add refresh button without stretch

        # Add Close Button
        self.close_button = QPushButton("X")
        self.close_button.setObjectName("closeButton")
        self.close_button.setToolTip("关闭抽屉")
        self.close_button.clicked.connect(self.closeRequested.emit)
        self.header_layout.addWidget(
            self.close_button, 0
        )  # Add close button without stretch

        # self.available_label_width = calculate_available_label_width(
        #     self, self.header_layout, self.folder_icon_label, self.refresh_button, self.close_button
        # ) # Removed: Calculation moved to _update_folder_label_elided_text

        return self.header_layout

    def update_content(self, path: str) -> None:
        """
        更新显示的文件夹路径及内容，始终同步刷新缓存，避免卡在“正在加载...”
        """
        file_list = None
        if self.controller:
            # 先同步刷新缓存，再取最新数据
            self.controller.data_manager.reload_drawer_content(path)
            file_list = self.controller.get_preloaded_file_list(path)
        self.update_with_file_list(path, file_list)

    def update_with_file_list(
        self, folder_path: str, file_list: Optional[List]
    ) -> None:
        """
        使用提供的文件列表刷新内容
        """
        self.current_folder = folder_path
        if self.folder_label:
            self.folder_label.setText(folder_path)
            self.folder_label.setToolTip(folder_path)

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

        # 强制刷新界面
        self.update()
        self.repaint()

    def _start_async_icon_loading(self):
        """Starts background tasks to load real icons for visible items."""
        if not self.items:
            return
        logging.debug(
            f"Starting async icon load for {len(self.items)} items in {self.current_folder}"
        )
        for item_widget in self.items:
            if isinstance(item_widget, FileIconWidget):  # Ensure it's the right type
                signals = IconWorkerSignals()
                # Connect signal to the slot *before* starting worker
                signals.icon_loaded.connect(self._on_icon_loaded)
                signals.error.connect(self._on_icon_load_error)
                worker = IconLoadWorker(item_widget.file_path, item_widget, signals)
                self.icon_load_pool.start(worker)

    @Slot(QWidget, QIcon)
    def _on_icon_loaded(self, widget: QWidget, icon: QIcon):
        """Slot to receive loaded icons and update the widget."""
        # Check if the widget still exists and belongs to the current view
        if isinstance(widget, FileIconWidget) and widget in self.items:
            # Check if the current_folder hasn't changed since the task started
            if os.path.dirname(widget.file_path) == self.current_folder:
                widget.set_icon(icon, self.icon_size)
            else:
                logging.debug(
                    f"Ignoring loaded icon for {widget.file_path} as folder changed."
                )
        else:
            logging.debug("Ignoring loaded icon for widget not found or invalid type.")

    @Slot(str, str)
    def _on_icon_load_error(self, file_path: str, error_message: str):
        """Slot to handle icon loading errors."""
        # Find the widget corresponding to the path? Might be slow.
        # Or just log the error.
        logging.warning(f"Failed to load icon for {file_path}: {error_message}")
        # Optionally update the widget with an 'error' icon?

    def _refresh_content(self) -> None:
        """
        刷新当前文件夹的内容
        强制重新扫描当前文件夹并刷新内容，绕过预加载缓存。
        """
        if self.current_folder and self.controller:
            logging.info(f"Force refreshing content for: {self.current_folder}")
            try:
                # 通过 DataManager 强制同步刷新
                new_file_list = self.controller.data_manager.reload_drawer_content(
                    self.current_folder
                )
                # Update the view with the newly fetched list
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
        """
        打开当前设置的文件夹
        """
        if os.path.isdir(self.current_folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_folder))

    def _create_file_item_placeholder(
        self, file_info: "FileInfo", placeholder_icon: QIcon
    ) -> FileIconWidget:
        """
        Creates a file item widget with a placeholder icon.
        """
        container_widget = FileIconWidget(file_info.path, file_info.is_dir)
        container_widget.setFixedSize(self.item_size[0], self.item_size[1])

        # 使用FileIconWidget的接口设置图标和文本
        container_widget.load_icon(placeholder_icon, self.icon_size)
        text_available_width = self.item_size[0] - 10  # 保留内边距
        container_widget.set_text(file_info.name, text_available_width)

        return container_widget

    def relayout_grid(self) -> None:
        """
        根据当前滚动区域视口（viewport）宽度重新排版文件项。
        """
        # Add checks for None before accessing attributes/methods
        if not self.grid_layout:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        if not self.items:
            return

        # Add checks for scroll_area and its viewport
        if not self.scroll_area or not self.scroll_area.viewport():
            return  # Cannot determine viewport width
        viewport_width = self.scroll_area.viewport().width()
        available_width = viewport_width

        # Add check for scroll_widget
        if available_width <= 0 and self.scroll_widget:
            available_width = self.scroll_widget.width()
        if available_width <= 0:
            available_width = self.width()
        if available_width <= 0:
            available_width = self.item_size[0] * 3  # Fallback

        item_total_width = self.item_size[0] + self.grid_layout.horizontalSpacing()
        if item_total_width <= 0:
            item_total_width = self.item_size[0]  # Fallback

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
        min_height += self.grid_layout.verticalSpacing()  # Add padding at the bottom

        # Add check for scroll_widget before setting height
        if self.scroll_widget:
            self.scroll_widget.setMinimumHeight(min_height)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handles resize events, relayouts grid and emits sizeChanged signal."""
        super().resizeEvent(event)
        self.relayout_grid()
        # Update folder label using the new method
        self._update_folder_label_elided_text()
        self.sizeChanged.emit(event.size())

    def clear_grid(self) -> None:
        """
        清空网格布局中的所有项
        """
        # Add check for None before accessing attributes/methods
        if not self.grid_layout:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Overrides paintEvent. Label update is now handled directly."""
        super().paintEvent(event)
        # No label update logic needed here anymore

    def _update_folder_label_elided_text(self) -> None:
        """
        Calculates available width and updates the folder label with elided text.
        """
        if (
            not self.current_folder
            or not self.folder_label
            or not self.header_layout
            or not self.folder_icon_label
            or not self.refresh_button  # Add check for refresh_button
            or not self.close_button
        ):
            return

        try:
            # Calculate available width dynamically each time, considering both buttons
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
            # Tooltip should always show the full path
            self.folder_label.setToolTip(self.current_folder)

        except Exception as e:
            logging.error(
                f"Error updating folder label text: {e}"
            )  # Use logging instead of print
            if self.folder_label:
                self.folder_label.setText("...")  # Fallback on error
                self.folder_label.setToolTip(self.current_folder)  # Still show tooltip

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

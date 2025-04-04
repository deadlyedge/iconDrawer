import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QGridLayout,
    QLabel,
    QSizePolicy,  # Import QSizePolicy
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
    QPixmap,
    QPaintEvent,  # Keep QPaintEvent import
)
from PySide6.QtCore import Qt, QSize, QUrl, Signal, QPoint
from typing import Optional, Callable

# Import refactored functions and necessary classes
from .custom_size_grip import CustomSizeGrip
from .icon_utils import get_icon_for_path

from .content_utils import calculate_available_label_width
from .content_utils import truncate_text  # Keep truncate_text for file names


class FileIconWidget(QWidget):
    """
    用于显示文件图标和文件名的部件
    """

    def __init__(self, file_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_path = file_path

        self.visual_container = QWidget(self)
        self.visual_container.setProperty("isVisualContainer", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.visual_container)

        self.content_layout = QVBoxLayout(self.visual_container)
        self.content_layout.setContentsMargins(0, 5, 0, 5)
        self.content_layout.setSpacing(2)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        双击打开文件或文件夹
        """
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mouseDoubleClickEvent(event)


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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.current_folder = ""
        # Initialize first
        self.icon_size = QSize(96, 96)
        self.item_size = (100, 120)
        self.items = []

        # Explicitly initialize UI elements to None before creation
        self.folder_label: Optional[QLabel] = None
        self.folder_icon_label: Optional[QLabel] = None
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

    def _init_main_container(self) -> None:
        """
        初始化主视觉容器，包括头部、滚动区域和大小调整手柄
        """
        self.main_visual_container = QWidget(self)
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
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(5)
        self.scroll_area.setWidget(self.scroll_widget)
        container_layout.addWidget(self.scroll_area, 1, 0)

        self.size_grip = CustomSizeGrip(self.main_visual_container)
        self.size_grip.resizeFinished.connect(self.resizeFinished.emit)
        container_layout.addWidget(
            self.size_grip,
            2,
            0,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )

        container_layout.setRowStretch(0, 0)
        container_layout.setRowStretch(1, 1)
        container_layout.setRowStretch(2, 0)
        container_layout.setColumnStretch(0, 1)

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
        self.folder_icon_label.setPixmap(QIcon("asset/folder_icon.png").pixmap(16))
        folder_layout.addWidget(self.folder_icon_label)  # Add to inner layout

        self.folder_label = QLabel(
            "", self.folder_container
        )  # Initialize with empty string
        # Use default size policy for label, let container handle expansion
        folder_layout.addWidget(
            self.folder_label, 1, Qt.AlignmentFlag.AlignLeft
        )  # Add to inner layout with stretch

        self.folder_container.click_callback = self.open_current_folder
        self.header_layout.addWidget(
            self.folder_container, 1
        )  # Add container with stretch

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("closeButton")
        self.close_button.clicked.connect(self.closeRequested.emit)
        self.header_layout.addWidget(self.close_button, 0)  # Add button without stretch

        # self.available_label_width = calculate_available_label_width(
        #     self, self.header_layout, self.folder_icon_label, self.close_button
        # ) # Removed: Calculation moved to _update_folder_label_elided_text

        return self.header_layout

    def update_content(self, folder_path: str) -> None:
        """
        更新显示的文件夹路径及内容
        """
        self.current_folder = folder_path
        if self.folder_label:
            self.folder_label.setText(folder_path)
            self.folder_label.setToolTip(folder_path)
        # Clear grid first
        self.clear_grid()
        self.items.clear()
        if not os.path.isdir(folder_path):
            if self.folder_label:
                self.folder_label.setText("")  # Clear label if path invalid
            return

        try:
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    full_path = os.path.join(folder_path, entry.name)
                    icon = get_icon_for_path(full_path)
                    container_widget = self._create_file_item(
                        full_path, entry.name, icon
                    )
                    self.items.append(container_widget)
            self.relayout_grid()
            # Update folder label using the new method
            self._update_folder_label_elided_text()
        except OSError as e:
            QMessageBox.critical(self, "错误", f"读取文件夹内容时出错: {e!s}")

    def open_current_folder(self) -> None:
        """
        打开当前设置的文件夹
        """
        if os.path.isdir(self.current_folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_folder))

    def _create_file_item(
        self, full_path: str, entry: str, icon: QIcon
    ) -> FileIconWidget:
        """
        创建显示单个文件项的部件
        """
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pixmap = icon.pixmap(self.icon_size)
        if (
            pixmap.width() > self.icon_size.width()
            or pixmap.height() > self.icon_size.height()
        ):
            pixmap = pixmap.scaled(
                self.icon_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        icon_label.setPixmap(pixmap)
        icon_label.setStyleSheet("background-color: transparent;")

        text_label = QLabel(entry)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        text_available_width = self.item_size[0] - 10
        text_label.setMinimumWidth(text_available_width)
        display_text = truncate_text(
            entry, text_label, text_available_width
        )  # Keep using util for item names
        text_label.setText(display_text)
        text_label.setToolTip(entry)
        text_label.setStyleSheet("background-color: transparent;")

        container_widget = FileIconWidget(full_path)
        container_widget.setFixedSize(self.item_size[0], self.item_size[1])
        container_widget.content_layout.addWidget(
            icon_label, 0, Qt.AlignmentFlag.AlignCenter
        )
        container_widget.content_layout.addWidget(
            text_label, 0, Qt.AlignmentFlag.AlignCenter
        )
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
        if not self.current_folder or not self.folder_label or not self.header_layout or not self.folder_icon_label or not self.close_button:
            # print("[DEBUG UpdateLabel] Missing widgets, skipping update.") # Optional debug
            return

        try:
            # Calculate available width dynamically each time
            available_width = calculate_available_label_width(
                self, self.header_layout, self.folder_icon_label, self.close_button
            )

            fm = QFontMetrics(self.folder_label.font())
            elided_text = fm.elidedText(
                self.current_folder, Qt.TextElideMode.ElideLeft, available_width
            )
            # Use the original debug format for comparison
            label_width = self.folder_label.width() # Current actual label width (might be small)
            container_width = self.folder_container.width() if self.folder_container else 0 # Current container width
            print(
                f"[DEBUG _update_folder_label] LabelW={label_width}, ContW={container_width}, AvailW={available_width}, Text='{elided_text}'"
            ) # DEBUG using calculated width
            self.folder_label.setText(elided_text)
            # Tooltip should always show the full path
            self.folder_label.setToolTip(self.current_folder)

        except Exception as e:
            print(f"Error updating folder label text: {e}")
            if self.folder_label:
                self.folder_label.setText("...") # Fallback on error
                self.folder_label.setToolTip(self.current_folder) # Still show tooltip

import os
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
)
from PySide6.QtCore import Qt, QSize, QUrl, Signal, QPoint
from typing import Optional, Callable

from .custom_size_grip import CustomSizeGrip


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

    def mouseDoubleClickEvent(self, event) -> None:
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
        # self._is_resizing_with_grip: bool = False # No longer needed
        self._init_main_container()
        self.icon_size = QSize(64, 64)
        self.item_size = (80, 100)
        self.items = []

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
        # Connect the custom grip's signal to the widget's signal
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
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 2, 5, 2)

        self.folder_container = ClickableWidget(self)
        self.folder_container.setProperty("isFolderPathLayout", True)
        folder_layout = QHBoxLayout(self.folder_container)
        folder_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_icon_label = QLabel(self.folder_container) # Store as instance variable
        self.folder_icon_label.setPixmap(QIcon("asset/folder_icon.png").pixmap(16))
        folder_layout.addWidget(self.folder_icon_label)

        self.folder_label = QLabel("", self.folder_container) # Initialize with empty string
        folder_layout.addWidget(self.folder_label, 1, Qt.AlignmentFlag.AlignLeft)

        self.folder_container.click_callback = self.open_current_folder

        header_layout.addWidget(self.folder_container, 1)

        self.close_button = QPushButton("X") # Store as instance variable
        self.close_button.setObjectName("closeButton")
        self.close_button.clicked.connect(self.closeRequested.emit)
        header_layout.addWidget(self.close_button, 0)

        self.header_layout = header_layout # Store layout
        return header_layout

    def update_content(self, folder_path: str) -> None:
        """
        更新显示的文件夹路径及内容
        """
        self.current_folder = folder_path
        self._update_folder_label_text() # Use helper method
        self.folder_label.setToolTip(folder_path)

        self.clear_grid()
        self.items.clear()
        if not os.path.isdir(folder_path):
            return

        try:
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    # if entry.name.startswith('.'):
                    #     continue
                    full_path = os.path.join(folder_path, entry.name)
                    icon = self._get_icon_for_path(full_path)
                    container_widget = self._create_file_item(
                        full_path, entry.name, icon
                    )
                    self.items.append(container_widget)
            self.relayout_grid()
        except OSError as e:
            QMessageBox.critical(self, "错误", f"读取文件夹内容时出错: {e!s}")

    def open_current_folder(self) -> None:
        """
        打开当前设置的文件夹
        """
        if os.path.isdir(self.current_folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_folder))

    def _get_icon_for_path(self, full_path: str) -> QIcon:
        """
        根据路径获取相应的图标
        """
        if os.path.isfile(full_path):
            icon = QIcon(full_path)
            if icon.isNull():
                icon = QIcon.fromTheme(
                    "text-x-generic",
                    QIcon(
                        ":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png"
                    ),
                )
        elif os.path.isdir(full_path):
            icon = QIcon("asset/folder_icon.png")
        else:
            icon = QIcon.fromTheme(
                "unknown",
                QIcon(
                    ":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png"
                ),
            )
        return icon

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
        text_label.setMinimumWidth(self.item_size[0] - 10)
        display_text = self._truncate_text(entry, text_label)
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

    def _truncate_text(self, text: str, label: QLabel) -> str:
        """
        根据空间大小截断文本以适应显示 (max 2 lines)
        """
        fm = QFontMetrics(label.font())
        available_width = self.item_size[0] - 4
        if available_width <= 0:
            available_width = 50

        avg_char_width = fm.averageCharWidth()
        if avg_char_width <= 0:
            avg_char_width = 6
        chars_per_line = max(1, available_width // avg_char_width)

        elided_line1 = fm.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
        if (
            fm.boundingRect(elided_line1).width() <= available_width
            and "\n" not in elided_line1
        ):
            if elided_line1 == text:
                return text

        max_chars_two_lines = chars_per_line * 2
        if len(text) > max_chars_two_lines:
            truncated_text = text[: max_chars_two_lines - 3] + "..."
        else:
            truncated_text = text

        return truncated_text

    def relayout_grid(self) -> None:
        """
        根据当前滚动区域视口（viewport）宽度重新排版文件项。
        """
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        if not self.items:
            return

        viewport_width = self.scroll_area.viewport().width()
        available_width = viewport_width

        if available_width <= 0:
            available_width = self.scroll_widget.width()
        if available_width <= 0:
            available_width = self.width()
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
        self.scroll_widget.setMinimumHeight(min_height)

        self.scroll_widget.setMinimumHeight(min_height)

        self.grid_layout.activate()
        self.scroll_widget.adjustSize()
        self.scroll_widget.updateGeometry()

    # mousePressEvent and mouseReleaseEvent are no longer needed here,
    # as the CustomSizeGrip handles its own mouse events.

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handles resize events, relayouts grid and emits sizeChanged signal."""
        super().resizeEvent(event)
        self.relayout_grid()
        self._update_folder_label_text() # Use helper method
        self.sizeChanged.emit(event.size())

    def clear_grid(self) -> None:
        """
        清空网格布局中的所有项
        """
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _calculate_available_label_width(self) -> int:
        """Calculate the available width for the folder label in the header."""
        if not hasattr(self, 'header_layout') or not hasattr(self, 'folder_icon_label') or not hasattr(self, 'close_button'):
             # Widgets might not be fully initialized yet
             return 100 # Return a default small width

        total_width = self.main_visual_container.width()
        margins = self.header_layout.contentsMargins()
        spacing = self.header_layout.spacing()

        # Width occupied by other elements
        icon_width = self.folder_icon_label.width()
        button_width = self.close_button.width()

        # Calculate available width
        # Total width - left margin - right margin - icon width - spacing before label - spacing after label container - button width
        # Note: folder_container stretches, so we subtract fixed elements and margins/spacing around it.
        # The spacing inside folder_container (between icon and label) is handled by its own layout.
        # We need the space allocated to folder_container first.
        # A simpler approach might be: container width - margins - button width - spacing
        container_width = self.folder_container.width()
        folder_layout = self.folder_container.layout() # Get the layout

        if not folder_layout:
             # Layout not yet available, return default
             # print("[DEBUG] Calc Width: Folder layout not found!")
             return 100

        folder_layout_margins = folder_layout.contentsMargins()
        folder_layout_spacing = folder_layout.spacing()

        available_width = (container_width -
                           folder_layout_margins.left() -
                           folder_layout_margins.right() -
                           self.folder_icon_label.width() -
                           folder_layout_spacing) # Space between icon and label

        # Add a small buffer for safety
        available_width -= 5

        # print(f"[DEBUG] Calc Width: ContW={container_width}, IconW={self.folder_icon_label.width()}, Spacing={folder_layout_spacing}, Avail={available_width}")

        return max(20, available_width) # Ensure a minimum width

    def _update_folder_label_text(self) -> None:
        """Updates the folder label text with elided version based on available width."""
        if not self.current_folder or not hasattr(self, 'folder_label'):
            return

        available_width = self._calculate_available_label_width()
        fm = QFontMetrics(self.folder_label.font())
        elided_text = fm.elidedText(
            self.current_folder, Qt.TextElideMode.ElideLeft, available_width
        )
        # print(f"[DEBUG] Update Label: AvailW={available_width}, Text='{elided_text}'") # DEBUG
        self.folder_label.setText(elided_text)

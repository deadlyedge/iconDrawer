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
from PySide6.QtGui import QIcon, QDesktopServices, QFontMetrics
from PySide6.QtCore import Qt, QSize, QUrl, Signal
from typing import Optional


class FileIconWidget(QWidget):
    def __init__(self, file_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_path = file_path

        # 创建内部视觉容器，用于显示具体内容和悬停效果
        self.visual_container = QWidget(self)
        self.visual_container.setProperty("isVisualContainer", True)

        # 主布局仅包含 visual_container
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.visual_container)

        # visual_container 内部布局
        self.content_layout = QVBoxLayout(self.visual_container)
        self.content_layout.setContentsMargins(0, 5, 0, 5)
        self.content_layout.setSpacing(2)

    def mouseDoubleClickEvent(self, event):
        # 双击打开文件或文件夹
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mouseDoubleClickEvent(event)


class DrawerContentWidget(QWidget):
    closeRequested = Signal()  # 关闭请求信号

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_main_container()
        self.icon_size = QSize(64, 64)        # 图标大小
        self.item_size = (80, 100)            # 文件项固定尺寸
        self.items = []                     # 存储所有文件项

    def _init_main_container(self) -> None:
        # 创建主视觉容器（用于添加头部和滚动区域）
        self.main_visual_container = QWidget(self)
        self.main_visual_container.setProperty("isDrawerContentContainer", True)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_visual_container)

        container_layout = QVBoxLayout(self.main_visual_container)
        container_layout.setContentsMargins(1, 1, 1, 1)  # 细微边距用于显示边框
        container_layout.setSpacing(0)

        # 添加头部（右上角关闭按钮）
        header_layout = self._create_header()
        container_layout.addLayout(header_layout)

        # 创建滚动区域，并在内部放置网格布局
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(5)
        self.scroll_area.setWidget(self.scroll_widget)

        container_layout.addWidget(self.scroll_area)

    def _create_header(self) -> QHBoxLayout:
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch()

        close_button = QPushButton("X")
        close_button.setFixedSize(12, 12)
        close_button.clicked.connect(self.closeRequested.emit)
        header_layout.addWidget(close_button)

        return header_layout

    def update_content(self, folder_path: str) -> None:
        self.clear_grid()
        self.items.clear()
        if not os.path.isdir(folder_path):
            return

        try:
            for entry in os.listdir(folder_path):
                full_path = os.path.join(folder_path, entry)
                icon = self._get_icon_for_path(full_path)
                container_widget = self._create_file_item(full_path, entry, icon)
                self.items.append(container_widget)
            self.relayout_grid()
        except OSError as e:
            QMessageBox.critical(self, "错误", f"读取文件夹内容时出错: {e}")

    def _get_icon_for_path(self, full_path: str) -> QIcon:
        if os.path.isfile(full_path):
            icon = QIcon(full_path)
            if icon.isNull():
                icon = QIcon.fromTheme("text-x-generic")
        else:
            icon = QIcon("asset/folder_icon.png")
        return icon

    def _create_file_item(self, full_path: str, entry: str, icon: QIcon) -> FileIconWidget:
        # 创建图标标签
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        icon_label.setPixmap(icon.pixmap(self.icon_size))
        icon_label.setStyleSheet("background-color: transparent;")

        # 创建文本标签，并进行文本截断
        text_label = QLabel(entry)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        display_text = self._truncate_text(entry, text_label)
        text_label.setText(display_text)
        text_label.setToolTip(entry)
        text_label.setStyleSheet("background-color: transparent;")

        # 使用 FileIconWidget 作为容器
        container_widget = FileIconWidget(full_path)
        container_widget.setFixedSize(self.item_size[0], self.item_size[1])
        container_widget.content_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        container_widget.content_layout.addWidget(text_label, 0, Qt.AlignmentFlag.AlignCenter)
        return container_widget

    def _truncate_text(self, text: str, label: QLabel) -> str:
        fm = QFontMetrics(label.font())
        available_width = self.item_size[0] - 4  # 扣除左右边距
        if available_width <= 0:
            available_width = 50  # 默认宽度

        avg_char_width = fm.averageCharWidth() or 6
        chars_per_line = max(1, available_width // avg_char_width)
        max_chars = chars_per_line * 2  # 估计显示2行文字

        if len(text) <= max_chars:
            return text
        else:
            return text[: max_chars - 3] + "..."

    def relayout_grid(self) -> None:
        # 清空当前网格布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # 根据内部滚动区域宽度重新计算每行可放置的列数
        available_width = self.scroll_widget.width() or self.width()
        columns = max(1, available_width // (self.item_size[0] + self.grid_layout.spacing()))
        row, col = 0, 0
        for item in self.items:
            self.grid_layout.addWidget(item, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.relayout_grid()

    def clear_grid(self) -> None:
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
                self.grid_layout.removeItem(item)

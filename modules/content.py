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
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import Qt, QSize, QUrl, Signal
from typing import Optional


class FileIconWidget(QWidget):
    def __init__(self, file_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_path = file_path

        # 创建内部视觉容器，用于显示内容和悬停效果
        self.visual_container = QWidget(self)
        self.visual_container.setProperty(
            "isVisualContainer", True
        )  # 设置自定义属性以便 QSS 选择

        # FileIconWidget 的主布局，只包含 visual_container
        main_container_layout = QVBoxLayout(self)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.addWidget(self.visual_container)
        self.setLayout(main_container_layout)

        # visual_container 的布局，包含图标和文本（将在 update_content 中填充）
        self.content_layout = QVBoxLayout(self.visual_container)
        self.content_layout.setContentsMargins(0, 5, 0, 5)
        self.content_layout.setSpacing(2)
        self.visual_container.setLayout(self.content_layout)

    def mouseDoubleClickEvent(self, event):
        # 双击时打开文件或文件夹 (事件仍在 FileIconWidget 上捕获)
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mouseDoubleClickEvent(event)


class DrawerContentWidget(QWidget):
    closeRequested = Signal()  # 添加关闭请求信号

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # DrawerContentWidget 本身保持透明
        # self.setStyleSheet("background-color: transparent;") # QSS 会处理

        # 创建主视觉容器
        self.main_visual_container = QWidget(self)
        self.main_visual_container.setProperty("isDrawerContentContainer", True) # 设置自定义属性

        # DrawerContentWidget 的主布局，只包含主视觉容器
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_visual_container)
        self.setLayout(outer_layout)

        # 主视觉容器的内部布局
        container_layout = QVBoxLayout(self.main_visual_container)
        container_layout.setContentsMargins(1, 1, 1, 1) # 添加细微边距以显示边框
        container_layout.setSpacing(0)
        self.main_visual_container.setLayout(container_layout)

        # --- 原有的内容现在添加到 container_layout ---
        # 添加右上角的关闭按钮
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        header_layout.setContentsMargins(0, 0, 0, 0)

        close_button = QPushButton("X")
        close_button.setFixedSize(12, 12)
        close_button.clicked.connect(self.closeRequested.emit)  # 连接到信号发射

        header_layout.addWidget(close_button)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # 创建滚动区域内部的部件和网格布局
        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_widget)

        # 将 header 和 scroll_area 添加到 container_layout
        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.scroll_area)

        self.icon_size = QSize(64, 64)  # 图标大小
        self.item_size = (80, 100)  # 每个文件项近似正方形的大小
        self.items = []  # 保存所有创建的文件项

    def update_content(self, folder_path: str) -> None:
        self.clear_grid()
        self.items = []
        if os.path.isdir(folder_path):
            try:
                for entry in os.listdir(folder_path):
                    full_path = os.path.join(folder_path, entry)
                    if os.path.isfile(full_path):
                        icon = QIcon(full_path)
                        if icon.isNull():
                            icon = QIcon.fromTheme("text-x-generic")
                    else:
                        icon = QIcon("asset/folder_icon.png")

                    # 创建图标标签
                    icon_label = QLabel()
                    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    icon_label.setSizePolicy(
                        QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                    )
                    pixmap = icon.pixmap(self.icon_size)
                    icon_label.setPixmap(pixmap)
                    icon_label.setStyleSheet(
                        "background-color: transparent;"
                    )  # 确保图标标签背景透明

                    # 创建文本标签
                    text_label = QLabel(entry)
                    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    text_label.setWordWrap(True)
                    text_label.setStyleSheet(
                        "background-color: transparent;"
                    )  # 确保文本标签背景透明

                    # 使用 FileIconWidget 作为容器，设置固定近似正方形尺寸
                    # 创建 FileIconWidget 实例
                    container_widget = FileIconWidget(full_path)
                    container_widget.setFixedSize(self.item_size[0], self.item_size[1])

                    # 将图标和文本添加到 container_widget 内部的 visual_container 的布局中
                    container_widget.content_layout.addWidget(
                        icon_label, 0, Qt.AlignmentFlag.AlignCenter
                    )
                    container_widget.content_layout.addWidget(
                        text_label, 0, Qt.AlignmentFlag.AlignCenter
                    )

                    self.items.append(container_widget)  # 添加到 items 列表
                self.relayout_grid()
            except OSError as e:
                QMessageBox.critical(self, "错误", f"读取文件夹内容时出错: {e}")
        else:
            self.clear_grid()

    def relayout_grid(self):
        # 清空布局中的部件
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        # 根据滚动区域内部部件的宽度计算每行可放置的列数
        available_width = self.scroll_widget.width() or self.width()
        columns = max(
            1, available_width // (self.item_size[1] + self.grid_layout.spacing())
        )
        row = 0
        col = 0
        for item in self.items:
            self.grid_layout.addWidget(item, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout_grid()

    def clear_grid(self) -> None:
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()
                self.grid_layout.removeItem(item)

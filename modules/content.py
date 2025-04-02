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

    def mouseDoubleClickEvent(self, event):
        # 双击时打开文件或文件夹
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mouseDoubleClickEvent(event)


class DrawerContentWidget(QWidget):
    closeRequested = Signal()  # 添加关闭请求信号

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # 主布局，包含一个可滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

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

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.scroll_area)

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

                    # 创建文本标签
                    text_label = QLabel(entry)
                    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    text_label.setWordWrap(True)

                    # 使用 FileIconWidget 作为容器，设置固定近似正方形尺寸
                    container = FileIconWidget(full_path)
                    container.setFixedSize(self.item_size[0], self.item_size[1])
                    container_layout = QVBoxLayout(container)
                    container_layout.setObjectName("file_container")
                    container_layout.setContentsMargins(5, 5, 5, 5)
                    container_layout.addWidget(icon_label)
                    container_layout.addWidget(text_label)

                    self.items.append(container)
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

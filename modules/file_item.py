import os
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QIcon, QMouseEvent, QDesktopServices
from PySide6.QtCore import QSize, Qt, QUrl

class FileIconWidget(QWidget):
    """
    用于显示文件图标和文件名的部件
    """
    def __init__(self, file_path: str, is_dir: bool, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("fileItem")
        self.file_path = file_path
        self.is_dir = is_dir
        self.icon_label: Optional[QLabel] = None  # 用于显示图标的标签

        self.visual_container = QWidget(self)
        self.visual_container.setObjectName("visualContainer")
        self.visual_container.setProperty("isVisualContainer", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.visual_container)

        self.content_layout = QVBoxLayout(self.visual_container)
        self.content_layout.setContentsMargins(0, 5, 0, 5)
        self.content_layout.setSpacing(2)

    def set_icon(self, icon: QIcon, icon_size: QSize):
        """设置图标，并缩放到指定大小。"""
        if self.icon_label:
            pixmap = icon.pixmap(icon_size)
            if pixmap.width() > icon_size.width() or pixmap.height() > icon_size.height():
                pixmap = pixmap.scaled(icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        双击打开文件或文件夹
        """
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mouseDoubleClickEvent(event)

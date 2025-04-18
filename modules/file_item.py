from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
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

        # 初始化图标标签
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.content_layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        # 初始化文本标签
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.content_layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignCenter)

    def set_icon(self, icon: QIcon, icon_size: QSize):
        """设置图标，并缩放到指定大小。"""
        if self.icon_label:
            pixmap = icon.pixmap(icon_size)
            if pixmap.width() > icon_size.width() or pixmap.height() > icon_size.height():
                pixmap = pixmap.scaled(icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)

    def set_text(self, text: str, max_width: int):
        """设置文本，自动截断以适应最大宽度。"""
        if self.text_label:
            from .content_utils import truncate_text
            display_text = truncate_text(text, self.text_label, max_width)
            self.text_label.setText(display_text)
            self.text_label.setToolTip(text)

    def load_icon(self, placeholder_icon: QIcon, icon_size: QSize):
        """
        读取并设置文件或文件夹的图标，若无法读取则使用占位图标。
        这里可以扩展为异步加载或缓存机制。
        """
        # 这里简单示例，直接使用传入的占位图标
        self.set_icon(placeholder_icon, icon_size)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        双击打开文件或文件夹
        """
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mouseDoubleClickEvent(event)

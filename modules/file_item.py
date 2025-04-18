from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtGui import QIcon, QMouseEvent, QDesktopServices
from PySide6.QtCore import QSize, Qt, QUrl, QThreadPool
from .icon_loader import IconWorkerSignals, IconLoadWorker
from .content_utils import truncate_text


class FileIconWidget(QWidget):
    """
    用于显示文件图标和文件名的部件
    """

    def __init__(
        self, file_path: str, is_dir: bool, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("fileItem")
        self.file_path = file_path
        self.is_dir = is_dir

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
        self.icon_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
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
            if (
                pixmap.width() > icon_size.width()
                or pixmap.height() > icon_size.height()
            ):
                pixmap = pixmap.scaled(
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            # pixmap = pixmap.scaled(icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)

    def set_text(self, text: str, max_width: int):
        """设置文本，自动截断以适应最大宽度。"""
        if self.text_label:
            display_text = truncate_text(text, self.text_label, max_width)
            self.text_label.setText(display_text)
            self.text_label.setToolTip(text)

    def load_icon(self, placeholder_icon: QIcon, icon_size: QSize):
        """
        读取并设置文件或文件夹的图标，若无法读取则使用占位图标。
        这里实现异步加载图标的逻辑，使用modules.icon_loader中的IconLoadWorker。
        """
        self._icon_size = icon_size  # 保存icon_size供回调使用
        # 先设置占位图标，防止加载延迟时无图标显示
        self.set_icon(placeholder_icon, icon_size)

        signals = IconWorkerSignals()
        signals.icon_loaded.connect(self._on_icon_loaded)
        signals.error.connect(self._on_icon_load_error)

        worker = IconLoadWorker(self.file_path, self, signals)
        QThreadPool.globalInstance().start(worker)

    def _on_icon_loaded(self, widget: QWidget, icon: QIcon):
        """Slot to receive loaded icons and update the widget."""
        if widget is self:
            self.set_icon(icon, self._icon_size)

    def _on_icon_load_error(self, file_path: str, error_message: str):
        """Slot to handle icon loading errors."""
        pass

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        双击打开文件或文件夹
        """
        super().mouseDoubleClickEvent(event)
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))

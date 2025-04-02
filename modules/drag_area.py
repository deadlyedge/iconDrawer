from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QPoint, Signal # Import Signal
from PySide6.QtGui import QIcon
from typing import Optional


class DragArea(QWidget):
    # Define signal
    settingsRequested = Signal()

    """
    一个用于拖拽窗口的区域，同时包含拖拽图标和设置图标。
    增强了高度和背景色，以提高可见性，并确保设置按钮可见。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # self.setFixedSize(200, 40)
        # self.setStyleSheet("background-color: rgba(0, 0, 0, 200);") # Style moved to QSS
        self._dragPos: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # 拖拽图标（汉堡图标），字号增大
        self.dragLabel = QLabel("☰", self)
        # self.dragLabel.setStyleSheet("font-size: 28px; color: white;") # Style moved to QSS
        layout.addWidget(self.dragLabel)

        layout.addStretch()

        # 设置图标按钮
        self.settingsButton = QPushButton(self)
        settings_icon = QIcon.fromTheme("preferences-system")
        if settings_icon.isNull():
            self.settingsButton.setText("设置")
        else:
            self.settingsButton.setIcon(settings_icon)
        self.settingsButton.setFixedSize(40, 40)
        # self.settingsButton.setStyleSheet( # Style moved to QSS
        #     "background-color: transparent; border: none; color: white;"
        # )
        layout.addWidget(self.settingsButton)

        self.settingsButton.clicked.connect(self.on_settings_clicked)

    def on_settings_clicked(self) -> None:
        # Emit signal instead of direct call
        self.settingsRequested.emit()
        # Remove direct call:
        # main_window = self.window()
        # from modules.main_window import MainWindow
        # if isinstance(main_window, MainWindow):
        #     main_window.open_settings()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            main_window = self.window()
            self._dragPos = (
                event.globalPosition().toPoint() - main_window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._dragPos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            main_window = self.window()
            newPos = event.globalPosition().toPoint() - self._dragPos
            main_window.move(newPos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._dragPos = None
        event.accept()

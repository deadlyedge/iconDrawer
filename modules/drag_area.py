from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QIcon
from typing import Optional


class DragArea(QWidget):
    settingsRequested = Signal()
    dragFinished = Signal()

    """
    一个用于拖拽窗口的区域，同时包含拖拽图标和设置图标。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dragArea")
        self._dragPos: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self.dragLabel = QLabel("☰ Drag Area ☰", self)
        self.dragLabel.setObjectName("dragLabel")
        layout.addWidget(self.dragLabel)

        layout.addStretch()

        self.settingsButton = QPushButton(self)
        settings_icon = QIcon.fromTheme("preferences-system")
        if settings_icon.isNull():
            self.settingsButton.setText("Settings")
        else:
            self.settingsButton.setIcon(settings_icon)
        self.settingsButton.setFixedSize(80, 30)
        self.settingsButton.setObjectName("settingsButton")
        layout.addWidget(self.settingsButton)

        self.settingsButton.clicked.connect(self.on_settings_clicked)

    def on_settings_clicked(self) -> None:
        self.settingsRequested.emit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            main_window = self.window()
            self._dragPos = (
                event.globalPosition().toPoint() - main_window.geometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._dragPos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            main_window = self.window()
            newPos = event.globalPosition().toPoint() - self._dragPos
            main_window.move(newPos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        was_dragging = self._dragPos is not None
        self._dragPos = None
        if was_dragging and event.button() == Qt.MouseButton.LeftButton:
            self.dragFinished.emit()
        event.accept()

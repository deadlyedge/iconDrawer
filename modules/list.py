from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
)
from PySide6.QtCore import Signal
from typing import Optional


class DrawerListWidget(QListWidget):
    itemSelected = Signal(QListWidgetItem)
    selectionCleared = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item:
            self.itemSelected.emit(item)
        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        self.selectionCleared.emit()
        super().leaveEvent(event)

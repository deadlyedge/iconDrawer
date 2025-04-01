from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
)
# from PySide6.QtCore import Qt, QPoint
from typing import Optional, cast


class DrawerListWidget(QListWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.locked: bool = False
        self.lockedItem: Optional[QListWidgetItem] = None
        self.setMouseTracking(True)
        # self.itemEntered.connect(self.on_item_entered)

    def on_item_entered(self, item: QListWidgetItem) -> None:
        if not self.locked:
            from modules.main_window import MainWindow
            main_win = cast(MainWindow, self.window())
            main_win.update_drawer_content(item)

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item:
            if self.locked:
                if item == self.lockedItem:
                    self.locked = False
                    self.lockedItem = None
            else:
                self.locked = True
                self.lockedItem = item

            from modules.main_window import MainWindow
            main_win = cast(MainWindow, self.window())
            main_win.update_drawer_content(item)
        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        if not self.locked:
            from modules.main_window import MainWindow
            main_win = cast(MainWindow, self.window())
            main_win.clear_drawer_content()
        super().leaveEvent(event)

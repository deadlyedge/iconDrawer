import os
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QIcon
from typing import Optional


class DrawerContentWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.listWidget = QListWidget()
        layout.addWidget(self.listWidget)

    def update_content(self, folder_path: str) -> None:
        self.listWidget.clear()
        if os.path.isdir(folder_path):
            try:
                for entry in os.listdir(folder_path):
                    full_path = os.path.join(folder_path, entry)
                    item = QListWidgetItem(entry)
                    if os.path.isfile(full_path):
                        icon = QIcon(full_path)
                        if icon.isNull():
                            icon = QIcon.fromTheme("text-x-generic")
                    else:
                        icon = QIcon.fromTheme("folder")
                    item.setIcon(icon)
                    self.listWidget.addItem(item)
            except OSError as e:
                print(f"读取文件夹内容时出错: {e}")
        else:
            self.listWidget.clear()

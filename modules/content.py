import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QSize
from typing import Optional


class DrawerContentWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        layout.addLayout(self.grid_layout)
        self.icon_size = QSize(64, 64)  # Set the desired icon size
        self.setMinimumWidth(640)

    def update_content(self, folder_path: str) -> None:
        # Clear the existing grid
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
            self.grid_layout.removeItem(self.grid_layout.itemAt(i))

        if os.path.isdir(folder_path):
            try:
                row = 0
                col = 0
                for entry in os.listdir(folder_path):
                    full_path = os.path.join(folder_path, entry)
                    if os.path.isfile(full_path):
                        icon = QIcon(full_path)
                        if icon.isNull():
                            icon = QIcon.fromTheme("text-x-generic")
                    else:
                        icon = QIcon.fromTheme("folder")

                    # Create a label to hold the icon and text
                    icon_label = QLabel()
                    icon_label.setAlignment(Qt.AlignCenter)
                    icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

                    # Set the icon
                    pixmap = icon.pixmap(self.icon_size)
                    icon_label.setPixmap(pixmap)

                    # Create a label for the text
                    text_label = QLabel(entry)
                    text_label.setAlignment(Qt.AlignCenter)
                    text_label.setWordWrap(True)

                    # Create a container widget for the icon and text
                    container = QWidget()
                    container_layout = QVBoxLayout(container)
                    container_layout.addWidget(icon_label)
                    container_layout.addWidget(text_label)
                    container_layout.setContentsMargins(5, 5, 5, 5)

                    # Add the container to the grid layout
                    self.grid_layout.addWidget(container, row, col)

                    col += 1
                    if col >= 3:  # Adjust the number of columns as needed
                        col = 0
                        row += 1

            except OSError as e:
                print(f"读取文件夹内容时出错: {e}")
        else:
            # Clear the existing grid
            for i in reversed(range(self.grid_layout.count())):
                widget = self.grid_layout.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()
                self.grid_layout.removeItem(self.grid_layout.itemAt(i))

import sys
import os
import json
from typing import Any, List, Dict, cast, Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# 使用整型常量代替 Qt.UserRole（其值为 32）
USER_ROLE: int = 32

CONFIG_FILE: str = "drawers.json"


class ConfigManager:
    @staticmethod
    def load_config() -> List[Dict[str, str]]:
        """
        加载配置文件，并验证每个抽屉数据必须为包含字符串字段 'name' 和 'path' 的字典。
        """
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                drawers = data.get("drawers", [])
                if isinstance(drawers, list):
                    valid_drawers: List[Dict[str, str]] = []
                    for drawer in drawers:
                        if (
                            isinstance(drawer, dict)
                            and isinstance(drawer.get("name"), str)
                            and isinstance(drawer.get("path"), str)
                        ):
                            valid_drawers.append(drawer)
                    return valid_drawers
            except (json.JSONDecodeError, OSError) as e:
                print(f"加载配置错误: {e}")
        return []

    @staticmethod
    def save_config(drawers: List[Dict[str, str]]) -> None:
        """
        保存抽屉配置，要求 drawers 为包含 'name' 和 'path' 键的字典列表。
        """
        data = {"drawers": drawers}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"保存配置错误: {e}")


class DrawerListWidget(QListWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.locked: bool = False
        self.lockedItem: Optional[QListWidgetItem] = None
        self.setMouseTracking(True)
        self.itemEntered.connect(self.on_item_entered)

    def on_item_entered(self, item: QListWidgetItem) -> None:
        if not self.locked:
            main_win = cast(MainWindow, self.window())
            main_win.update_drawer_content(item)

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if item:
            self.locked = True
            self.lockedItem = item
            # 调用 update_drawer_content 替代重复的 lock_content 方法
            main_win = cast(MainWindow, self.window())
            main_win.update_drawer_content(item)
        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        if not self.locked:
            main_win = cast(MainWindow, self.window())
            main_win.clear_content()
        super().leaveEvent(event)


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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("图标抽屉管理")
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QHBoxLayout(centralWidget)

        # 左侧面板：抽屉列表及“添加抽屉”按钮
        leftPanel = QWidget()
        leftLayout = QVBoxLayout(leftPanel)
        self.drawerList = DrawerListWidget(leftPanel)
        leftLayout.addWidget(self.drawerList)
        self.addButton = QPushButton("添加抽屉")
        leftLayout.addWidget(self.addButton)
        self.addButton.clicked.connect(self.add_drawer)

        mainLayout.addWidget(leftPanel)

        # 右侧面板：抽屉内容显示
        self.drawerContent = DrawerContentWidget()
        mainLayout.addWidget(self.drawerContent)

        self.load_drawers()

    def load_drawers(self) -> None:
        drawers = ConfigManager.load_config()
        for drawer in drawers:
            name: str = drawer["name"]
            path: str = drawer["path"]
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, path)
            self.drawerList.addItem(item)

    def save_drawers(self) -> None:
        drawers: List[Dict[str, str]] = []
        for i in range(self.drawerList.count()):
            item: QListWidgetItem = self.drawerList.item(i)
            drawers.append({"name": item.text(), "path": item.data(USER_ROLE)})
        ConfigManager.save_config(drawers)

    def add_drawer(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            name = os.path.basename(folder)
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, folder)
            self.drawerList.addItem(item)
            self.save_drawers()

    def update_drawer_content(self, item: QListWidgetItem) -> None:
        folder = item.data(USER_ROLE)
        if isinstance(folder, str):
            self.drawerContent.update_content(folder)

    def clear_content(self) -> None:
        self.drawerContent.listWidget.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

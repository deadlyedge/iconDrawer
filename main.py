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
    QLabel,
    QDialog,
    QDialogButtonBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QPoint
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
        # self.itemEntered.connect(self.on_item_entered)

    def on_item_entered(self, item: QListWidgetItem) -> None:
        if not self.locked:
            main_win = cast(MainWindow, self.window())
            main_win.update_drawer_content(item)

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if item:
            if self.locked:
                if item == self.lockedItem:
                    self.locked = False
                    self.lockedItem = None
            else:
                self.locked = True
                self.lockedItem = item

            main_win = cast(MainWindow, self.window())
            main_win.update_drawer_content(item)
        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        if not self.locked:
            main_win = cast(MainWindow, self.window())
            main_win.clear_drawer_content()
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
        else:
            self.listWidget.clear()


class DragArea(QWidget):
    """
    一个用于拖拽窗口的区域，同时包含拖拽图标和设置图标。
    增强了高度和背景色，以提高可见性，并确保设置按钮可见。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(200, 60)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        self._dragPos: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # 拖拽图标（汉堡图标），字号增大
        self.dragLabel = QLabel("☰", self)
        self.dragLabel.setStyleSheet("font-size: 28px; color: white;")
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
        self.settingsButton.setStyleSheet(
            "background-color: transparent; border: none; color: white;"
        )
        layout.addWidget(self.settingsButton)

        self.settingsButton.clicked.connect(self.on_settings_clicked)

    def on_settings_clicked(self) -> None:
        main_window = self.window()
        if isinstance(main_window, MainWindow):
            main_window.open_settings()

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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("图标抽屉管理器")
        self.setWindowOpacity(0.8)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        # 主区域：水平布局划分左右两部分
        centralWidget = QWidget()
        centralWidget.setStyleSheet("background: transparent;")
        self.setCentralWidget(centralWidget)
        mainLayout = QHBoxLayout(centralWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)

        # 左侧面板：固定位置在窗口左侧偏上，包括dragarea和drawerlist及添加按钮
        leftPanel = QWidget()
        leftPanel.setFixedSize(210, 300)
        # leftPanel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        leftPanel.setStyleSheet("background: black;")

        leftLayout = QVBoxLayout(leftPanel)
        leftLayout.setContentsMargins(5, 5, 5, 5)
        leftLayout.setSpacing(10)

        # 固定dragarea：与drawerlist等宽，固定深色背景
        self.dragArea = DragArea(leftPanel)
        self.dragArea.setFixedSize(210, 60)
        leftLayout.addWidget(self.dragArea)

        # 固定drawerlist：固定大小，位于dragarea下方，窗口左边偏上
        self.drawerList = DrawerListWidget(leftPanel)
        self.drawerList.setFixedSize(210, 240)
        leftLayout.addWidget(self.drawerList)

        # 添加按钮，固定宽度
        self.addButton = QPushButton("添加抽屉", leftPanel)
        self.addButton.setFixedWidth(210)
        leftLayout.addWidget(self.addButton)
        self.addButton.clicked.connect(self.add_drawer)

        # leftLayout.addStretch()  # 保留顶部布局
        mainLayout.addWidget(leftPanel, alignment=Qt.AlignmentFlag.AlignTop)

        # 右侧面板：固定drawercontent的位置和大小，窗口右侧，高度超过drawerlist，未点选list时不可见
        rightPanel = QWidget()
        rightPanel.setFixedSize(600, 600)
        # rightPanel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        rightPanel.setStyleSheet("background: transparent;")

        rightLayout = QVBoxLayout(rightPanel)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(0)

        self.drawerContent = DrawerContentWidget()
        self.drawerContent.setFixedSize(600, 600)
        self.drawerContent.setStyleSheet("background-color: black;")
        self.drawerContent.setVisible(False)
        rightLayout.addWidget(self.drawerContent)

        # mainLayout.addWidget(self.drawerContent)

        mainLayout.addWidget(rightPanel, alignment=Qt.AlignmentFlag.AlignTop)
        mainLayout.addStretch()  # 保留顶部布局

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
            self.drawerContent.setVisible(True)

    def clear_drawer_content(self) -> None:
        self.drawerContent.listWidget.clear()
        self.drawerContent.setVisible(False)

    def open_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog_layout = QVBoxLayout(dialog)
        label = QLabel("此处为设置窗口。", dialog)
        dialog_layout.addWidget(label)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=dialog)
        button_box.accepted.connect(dialog.accept)
        dialog_layout.addWidget(button_box)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.resize(800, 600)
    mainWindow.show()
    sys.exit(app.exec())

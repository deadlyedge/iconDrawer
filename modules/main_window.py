import os
from typing import List, Dict
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidgetItem,
    QPushButton,
    QFileDialog,
    QLabel,
    QDialog,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt
from modules.config_manager import ConfigManager
from modules.list import DrawerListWidget
from modules.content import DrawerContentWidget
from modules.drag_area import DragArea


USER_ROLE: int = 32


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
        mainLayout.setSpacing(0)

        # 左侧面板：固定位置在窗口左侧偏上，包括dragarea和drawerlist及添加按钮
        leftPanel = QWidget()
        leftPanel.setFixedSize(210, 300)
        # leftPanel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        leftPanel.setStyleSheet("background: black;")

        leftLayout = QVBoxLayout(leftPanel)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(0)

        # 固定dragarea：与drawerlist等宽，固定深色背景
        self.dragArea = DragArea(leftPanel)
        # self.dragArea.setFixedSize(210, 32)
        leftLayout.addWidget(self.dragArea)

        # 固定drawerlist：固定大小，位于dragarea下方，窗口左边偏上
        self.drawerList = DrawerListWidget(leftPanel)
        self.drawerList.setFixedSize(210, 240)
        leftLayout.addWidget(self.drawerList)

        # 添加按钮，固定宽度
        self.addButton = QPushButton("添加抽屉", leftPanel)
        # self.addButton.setFixedWidth(210)
        leftLayout.addWidget(self.addButton)
        self.addButton.clicked.connect(self.add_drawer)

        # leftLayout.addStretch()  # 保留顶部布局
        mainLayout.addWidget(leftPanel, alignment=Qt.AlignmentFlag.AlignTop)

        # 右侧面板：固定drawercontent的位置和大小，窗口右侧，高度超过drawerlist，未点选list时不可见
        # rightPanel = QWidget()
        # rightPanel.setFixedSize(640, 640)
        # rightPanel.setContentsMargins(0, 0, 0, 0)

        # rightPanel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # rightPanel.setStyleSheet("background: yellow; border: 0;")

        # rightLayout = QVBoxLayout(rightPanel)
        # rightLayout.setContentsMargins(0, 0, 0, 0)
        # rightLayout.setSpacing(0)

        self.drawerContent = DrawerContentWidget()
        self.drawerContent.setFixedSize(640, 640)
        self.drawerContent.setStyleSheet("background-color: black; border: 0;")
        self.drawerContent.setVisible(False)
        self.drawerContent.setContentsMargins(0, 0, 0, 0)

        # rightLayout.addWidget(self.drawerContent)

        mainLayout.addWidget(self.drawerContent, alignment=Qt.AlignmentFlag.AlignTop)

        # mainLayout.addWidget(rightPanel, alignment=Qt.AlignmentFlag.AlignTop)
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
        self.drawerContent.layout.clear()
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

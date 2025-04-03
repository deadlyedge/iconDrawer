import os
from typing import List, Dict, Optional # Added Optional
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
from PySide6.QtCore import Qt, QPoint # Added QPoint
from modules.config_manager import ConfigManager
from modules.list import DrawerListWidget
from modules.content import DrawerContentWidget
from modules.drag_area import DragArea


USER_ROLE: int = 32


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._setup_window_properties()
        self._setup_ui()
        self._connect_signals()
        # Initialize state variables moved from DrawerListWidget
        self.locked: bool = False
        self.lockedItem: Optional[QListWidgetItem] = None
        # self._initial_position_loaded flag removed
        self.load_drawers()
        # self._initial_position_loaded = True removed

    def _setup_window_properties(self) -> None:
        """Sets the main window properties."""
        self.setWindowTitle("图标抽屉管理器")
        self.setWindowOpacity(0.8)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

    def _setup_ui(self) -> None:
        """Sets up the main UI layout and widgets."""
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        mainLayout = QHBoxLayout(centralWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        self._setup_left_panel(mainLayout)
        self._setup_right_panel(mainLayout)

        mainLayout.addStretch() # Keep content aligned to the top-left

    def _setup_left_panel(self, mainLayout: QHBoxLayout) -> None:
        """Creates and configures the left panel."""
        leftPanel = QWidget()
        leftPanel.setObjectName("leftPanel")
        leftPanel.setFixedSize(210, 300)

        leftLayout = QVBoxLayout(leftPanel)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(0)

        # Drag area
        self.dragArea = DragArea(leftPanel)
        leftLayout.addWidget(self.dragArea)

        # Drawer list
        self.drawerList = DrawerListWidget(leftPanel)
        self.drawerList.setFixedSize(210, 240)
        leftLayout.addWidget(self.drawerList)

        # Add button
        self.addButton = QPushButton("添加抽屉", leftPanel)
        self.addButton.setObjectName("addButton")
        leftLayout.addWidget(self.addButton)

        mainLayout.addWidget(leftPanel, alignment=Qt.AlignmentFlag.AlignTop)

    def _setup_right_panel(self, mainLayout: QHBoxLayout) -> None:
        """Creates and configures the right content panel."""
        self.drawerContent = DrawerContentWidget()
        self.drawerContent.setObjectName("drawerContent")
        self.drawerContent.setFixedSize(640, 640)
        self.drawerContent.setVisible(False)

        mainLayout.addWidget(self.drawerContent, alignment=Qt.AlignmentFlag.AlignTop)

    def _connect_signals(self) -> None:
        """Connects widget signals to slots."""
        # Button signal
        self.addButton.clicked.connect(self.add_drawer)

        # DrawerListWidget signals
        self.drawerList.itemSelected.connect(self.update_drawer_content) # Connect to updated slot
        self.drawerList.selectionCleared.connect(self.clear_drawer_content) # Connect to updated slot

        # DragArea signals
        self.dragArea.settingsRequested.connect(self.open_settings)
        self.dragArea.dragFinished.connect(self.save_drawers) # Connect drag finished to save

        # DrawerContentWidget signal
        self.drawerContent.closeRequested.connect(self.clear_drawer_content) # Connect close signal

    # --- Event Handlers ---

    # moveEvent removed

    # --- Public Methods and Slots ---

    def load_drawers(self) -> None:
        """Loads drawers and window position from config."""
        drawers, window_position = ConfigManager.load_config() # Get position too
        # Apply window position if available
        if window_position:
            self.move(window_position)

        # Load drawer items
        self.drawerList.clear() # Clear existing items before loading
        for drawer in drawers:
            name: str = drawer["name"]
            path: str = drawer["path"]
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, path)
            self.drawerList.addItem(item)

    def save_drawers(self) -> None:
        """Saves drawers and the current window position to config."""
        drawers: List[Dict[str, str]] = []
        for i in range(self.drawerList.count()):
            item: QListWidgetItem = self.drawerList.item(i)
            # Ensure path is stored correctly
            path_data = item.data(USER_ROLE)
            if isinstance(path_data, str):
                 drawers.append({"name": item.text(), "path": path_data})
            else:
                 print(f"警告：项目 '{item.text()}' 的路径数据无效，跳过保存。") # Warn if path is not a string

        current_position: QPoint = self.pos() # Get current window position
        ConfigManager.save_config(drawers, current_position) # Pass position to save_config

    def add_drawer(self) -> None:
        """Adds a new drawer and saves the configuration."""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            name = os.path.basename(folder)
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, folder)
            self.drawerList.addItem(item)
            self.save_drawers()

    # Updated slot to handle locking logic
    def update_drawer_content(self, item: QListWidgetItem) -> None:
        """Handles item selection and locking logic."""
        if self.locked:
            if item == self.lockedItem:
                # Unlock if the locked item is clicked again
                self.locked = False
                self.lockedItem = None
                # Optionally hide content when unlocking, or keep it visible
                # self.drawerContent.setVisible(False) # Uncomment if desired
                print("Drawer unlocked") # Debug print
            else:
                # If locked, but a different item is clicked, update content but stay locked
                folder = item.data(USER_ROLE)
                if isinstance(folder, str):
                    self.drawerContent.update_content(folder)
                    self.drawerContent.setVisible(True)
                self.lockedItem = item # Update the locked item
                print(f"Drawer remains locked, content updated to: {item.text()}") # Debug print

        else:
            # Lock and show content if not locked
            self.locked = True
            self.lockedItem = item
            folder = item.data(USER_ROLE)
            if isinstance(folder, str):
                self.drawerContent.update_content(folder)
                self.drawerContent.setVisible(True)
            print(f"Drawer locked on: {item.text()}") # Debug print


    # Updated slot to check lock state
    def clear_drawer_content(self) -> None:
        """Clears the content view only if the list is not locked."""
        if not self.locked:
            # self.drawerContent.layout.clear() # Clearing layout might not be needed
            self.drawerContent.setVisible(False)
            print("Drawer content cleared (unlocked)") # Debug print
        else:
            # Also handle the case where the close button (X) is clicked while locked
            # In this case, we should probably unlock and hide
            if self.sender() == self.drawerContent: # Check if called by DrawerContent's closeRequested signal
                 self.locked = False
                 self.lockedItem = None
                 self.drawerContent.setVisible(False)
                 print("Drawer content cleared (closed while locked)") # Debug print
            else:
                 print("Drawer content not cleared (locked by list selection)") # Debug print


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

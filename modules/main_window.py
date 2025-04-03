import os
from typing import List, Dict, Optional, TYPE_CHECKING
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
from PySide6.QtCore import Qt, QPoint, QSize, Signal
from PySide6.QtGui import QMoveEvent # Import QMoveEvent
# Import AppController conditionally for type hinting if needed, or directly
# from modules.controller import AppController # Direct import might cause issues if controller imports MainWindow
from modules.config_manager import DrawerDict # Keep DrawerDict if used in view methods
from modules.list import DrawerListWidget
from modules.content import DrawerContentWidget
from modules.drag_area import DragArea

# Forward declare AppController for type hints if direct import is problematic
if TYPE_CHECKING:
    from modules.controller import AppController

USER_ROLE: int = 32


class MainWindow(QMainWindow):
    # Signal emitted when the window is moved
    windowMoved = Signal(QPoint)

    def __init__(self) -> None:
        super().__init__()
        # Controller instance will be created after UI setup
        self.controller: Optional['AppController'] = None
        self._setup_window_properties()
        self._setup_ui()
        # Create controller *after* UI elements exist
        # Import locally to prevent circular import issues at module level
        from modules.controller import AppController
        self.controller = AppController(self)
        self._connect_signals()
        # Initial data loading is now handled by the controller's __init__

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
        self._setup_right_panel()

        mainLayout.addStretch(1)

    def _setup_left_panel(self, mainLayout: QHBoxLayout) -> None:
        """Creates and configures the left panel."""
        self.leftPanel = QWidget()
        self.leftPanel.setObjectName("leftPanel")
        self.leftPanel.setFixedSize(210, 300)

        leftLayout = QVBoxLayout(self.leftPanel)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(0)

        self.dragArea = DragArea(self.leftPanel)
        leftLayout.addWidget(self.dragArea)

        self.drawerList = DrawerListWidget(self.leftPanel)
        self.drawerList.setFixedSize(210, 240)
        leftLayout.addWidget(self.drawerList)

        self.addButton = QPushButton("添加抽屉", self.leftPanel)
        self.addButton.setObjectName("addButton")
        leftLayout.addWidget(self.addButton)

        mainLayout.addWidget(self.leftPanel, 0, alignment=Qt.AlignmentFlag.AlignTop)

    def _setup_right_panel(self) -> None:
        """Creates and configures the right content panel, parented to central widget."""
        self.drawerContent = DrawerContentWidget(self.centralWidget())
        self.drawerContent.setObjectName("drawerContent")
        self.drawerContent.setVisible(False)
        self.drawerContent.setMinimumSize(300, 200)

        self.content_spacing = 5

    def _connect_signals(self) -> None:
        """Connects UI signals to the controller's slots."""
        if not self.controller:
            print("Error: Controller not initialized during signal connection.")
            return

        # Button signal
        self.addButton.clicked.connect(self.controller.add_new_drawer)

        # DrawerListWidget signals
        self.drawerList.itemSelected.connect(self.controller.handle_item_selected)
        self.drawerList.selectionCleared.connect(self.controller.handle_selection_cleared)

        # DragArea signals
        self.dragArea.settingsRequested.connect(self.controller.handle_settings_requested)
        self.dragArea.dragFinished.connect(self.controller.handle_window_drag_finished) # Connect drag finished

        # DrawerContentWidget signals
        self.drawerContent.closeRequested.connect(self.controller.handle_content_close_requested)
        self.drawerContent.resizeFinished.connect(self.controller.handle_content_resize_finished)

        # MainWindow signal
        self.windowMoved.connect(self.controller.update_window_position)


    # --- Methods Called by Controller ---

    def populate_drawer_list(self, drawers: List[DrawerDict]) -> None:
        """Clears and populates the drawer list view with data from the controller."""
        self.drawerList.clear()
        for drawer_data in drawers:
            name = drawer_data.get("name", "Unnamed Drawer") # Provide default name
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, drawer_data) # Store the whole dict
            self.drawerList.addItem(item)

    def add_drawer_item(self, drawer: DrawerDict) -> None:
        """Adds a single drawer item to the list view."""
        name = drawer.get("name", "Unnamed Drawer")
        item = QListWidgetItem(name)
        item.setData(USER_ROLE, drawer)
        self.drawerList.addItem(item)

    def set_initial_position(self, pos: QPoint) -> None:
        """Sets the initial window position."""
        self.move(pos)

    def show_drawer_content(self, drawer_data: DrawerDict, target_size: QSize) -> None:
        """Adjusts window size, positions, updates, and shows the content widget."""
        folder_path = drawer_data.get("path")
        if not folder_path:
            print(f"Error: Cannot show content for drawer '{drawer_data.get('name')}' - path missing.")
            return

        # 1. Calculate required window size
        required_window_width = self.leftPanel.width() + self.content_spacing + target_size.width()
        required_window_height = max(self.leftPanel.height(), target_size.height())

        # 2. Resize main window first
        # Check if current size is already sufficient to avoid unnecessary shrinking/growing flicker
        current_geom = self.geometry()
        if current_geom.width() < required_window_width or current_geom.height() < required_window_height:
             self.resize(required_window_width, required_window_height)
        # If window is larger, we might want to keep it larger or shrink it.
        # For now, let's resize precisely. Consider adding logic if needed.
        elif current_geom.width() > required_window_width or current_geom.height() > required_window_height:
             self.resize(required_window_width, required_window_height)


        # 3. Resize and position content widget
        print(f"[show_drawer_content] Resizing content widget to: {target_size}") # DEBUG
        self.drawerContent.resize(target_size)
        # Ensure positioning happens after potential window resize
        self.drawerContent.move(self.leftPanel.width() + self.content_spacing, 0) # Align top

        # 4. Update content
        self.drawerContent.update_content(folder_path) # Pass only the path

        # 5. Make visible
        self.drawerContent.setVisible(True)
        self.drawerContent.raise_() # Ensure it's on top if overlapping somehow

    def hide_drawer_content(self) -> None:
        """Hides the content widget and resizes the main window."""
        if self.drawerContent.isVisible():
            self.drawerContent.setVisible(False)
            # Resize window back to fit only the left panel
            # Use fixed size of leftPanel for reliable sizing
            self.resize(self.leftPanel.width(), self.leftPanel.height())

    def prompt_for_folder(self) -> Optional[str]:
        """Shows a dialog to select a folder and returns the path."""
        # Ensure the dialog opens on top of the main window
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", options=QFileDialog.Option.ShowDirsOnly)
        return folder if folder else None

    def get_drawer_content_size(self) -> QSize:
        """Returns the current size of the drawer content widget."""
        current_size = self.drawerContent.size()
        print(f"[get_drawer_content_size] Returning size: {current_size}") # DEBUG
        return current_size

    def get_current_position(self) -> QPoint:
        """Returns the current top-left position of the main window."""
        return self.pos()

    def clear_list_selection(self) -> None:
        """Clears the current selection in the drawer list."""
        self.drawerList.clearSelection()
        # Optionally reset hover state if needed
        # self.drawerList.setCurrentItem(None)


    # --- Event Overrides ---

    def moveEvent(self, event: QMoveEvent) -> None:
        """Overrides the move event to emit the windowMoved signal."""
        super().moveEvent(event)
        # Emit signal only if the controller exists (to avoid issues during init)
        if hasattr(self, 'controller') and self.controller:
            self.windowMoved.emit(self.pos())

    # --- Settings Dialog ---

    def show_settings_dialog(self) -> None: # Renamed from open_settings
        """Shows the settings dialog."""
        # Keep the simple placeholder dialog for now
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog_layout = QVBoxLayout(dialog)
        label = QLabel("此处为设置窗口。", dialog)
        dialog_layout.addWidget(label)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=dialog)
        button_box.accepted.connect(dialog.accept)
        dialog_layout.addWidget(button_box)
        dialog.exec()

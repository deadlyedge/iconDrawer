from typing import List, Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidgetItem,
    QPushButton,
    QFileDialog,
    QSystemTrayIcon,
    QMenu,
    QApplication,  # Add QApplication import
)
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QCoreApplication, Slot
from PySide6.QtGui import QMoveEvent, QAction, QIcon, QCloseEvent
import logging  # Import logging

from modules.settings_manager import DrawerDict  # Import SettingsManager
from modules.list import DrawerListWidget
from modules.content import DrawerContentWidget
from modules.drag_area import DragArea
from modules.settings_dialog import SettingsDialog  # Import SettingsDialog

# Forward declare AppController for type hints if direct import is problematic
if TYPE_CHECKING:
    from modules.controller import AppController
# Import USER_ROLE from controller
from modules.controller import USER_ROLE


class MainWindow(QMainWindow):
    # Signal emitted when the window is moved
    windowMoved = Signal(QPoint)

    def __init__(self) -> None:
        super().__init__()
        # Controller instance will be created after UI setup
        self.controller: Optional["AppController"] = None
        self._setup_window_properties()
        self._setup_ui()
        # Create controller *after* UI elements exist
        # Import locally to prevent circular import issues at module level
        from modules.controller import AppController

        self.controller = AppController(self)

        # --- Create DrawerContentWidget *after* controller exists ---
        if not self.controller:
            # This should ideally not happen if AppController init succeeds
            logging.critical(
                "Controller failed to initialize before creating DrawerContentWidget!"
            )
            self.drawerContent = None  # Explicitly set to None
        else:
            # Pass the controller and the central widget container
            self.drawerContent = DrawerContentWidget(
                self.controller, self._central_widget_container
            )
            self.drawerContent.setObjectName("drawerContent")
            self.drawerContent.setVisible(False)
            self.drawerContent.setMinimumSize(300, 200)
            self.drawerContent.move(self.leftPanel.width() + self.content_spacing, 0)

        # 连接 controller 的解耦信号到 MainWindow 的私有方法
        if self.controller:
            self.controller.showDrawerContent.connect(self._on_show_drawer_content)
            self.controller.hideDrawerContent.connect(self._on_hide_drawer_content)
            # 如有 updateDrawerContent 信号可按需连接

        self._connect_signals()  # Connect signals *after* drawerContent is created
        self._create_tray_icon()  # Create tray icon and menu

        # Hide the window initially, show only the tray icon
        # self.hide() # Moved to main.py after controller setup potentially

    def _setup_window_properties(self) -> None:
        """Sets the main window properties."""
        self.setWindowTitle("iconDrawer")
        # self.setWindowOpacity(0.8)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        # Set object name for styling
        self.setObjectName("mainWindow")  # Or set on centralWidget if preferred

    def _setup_ui(self) -> None:
        """Sets up the main UI layout and widgets."""
        # Use a different name to avoid conflict with the centralWidget() method
        self._central_widget_container = QWidget()
        self._central_widget_container.setObjectName(
            "centralWidgetContainer"
        )  # Update object name too
        self.setCentralWidget(self._central_widget_container)

        mainLayout = QHBoxLayout(self._central_widget_container)
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

        self.addButton = QPushButton("Add Drawer", self.leftPanel)
        self.addButton.setObjectName("addButton")
        leftLayout.addWidget(self.addButton)

        mainLayout.addWidget(self.leftPanel, 0, alignment=Qt.AlignmentFlag.AlignTop)

    def _setup_right_panel(self) -> None:
        """Prepares variables related to the right content panel."""
        # DrawerContentWidget creation moved to __init__ after controller exists.
        # Initialize attribute to None here for clarity
        self.drawerContent: Optional[DrawerContentWidget] = None
        self.content_spacing = 5

    def _connect_signals(self) -> None:
        """Connects UI signals to the controller's slots."""
        if not self.controller:
            logging.error("Controller not initialized during signal connection.")
            return

        # Button signal
        self.addButton.clicked.connect(self.controller.add_new_drawer)

        # DrawerListWidget signals
        self.drawerList.itemSelected.connect(self.controller.handle_item_selected)
        self.drawerList.selectionCleared.connect(
            self.controller.handle_selection_cleared
        )

        # DragArea signals
        self.dragArea.settingsRequested.connect(
            self.controller.handle_settings_requested
        )
        self.dragArea.dragFinished.connect(
            self.controller.handle_window_drag_finished
        )  # Connect drag finished

        # DrawerContentWidget signals (check if drawerContent exists)
        if self.drawerContent:
            self.drawerContent.closeRequested.connect(
                self.controller.handle_content_close_requested
            )
            self.drawerContent.resizeFinished.connect(
                self.controller.handle_content_resize_finished
            )
            self.drawerContent.sizeChanged.connect(
                self._handle_content_size_changed
            )  # Connect size changed signal
        else:
            logging.error("DrawerContentWidget is None, cannot connect its signals.")

        # MainWindow signal
        self.windowMoved.connect(self.controller.update_window_position)

        # Apply initial background color (moved here after controller exists)
        self.apply_initial_background()

    # --- Methods Called by Controller ---

    def populate_drawer_list(self, drawers: List[DrawerDict]) -> None:
        """Clears and populates the drawer list view with data from the controller."""
        self.drawerList.clear()
        for drawer_data in drawers:
            name = drawer_data.get("name", "Unnamed Drawer")  # Provide default name
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, drawer_data)  # Store the whole dict
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

    # 解耦信号的私有处理方法
    def _on_show_drawer_content(self, drawer_data: DrawerDict, target_size: QSize) -> None:
        """响应 controller 的 showDrawerContent 信号，展示内容区域。"""
        folder_path = drawer_data.get("path")
        if not folder_path:
            logging.error(
                f"Cannot show content for drawer '{drawer_data.get('name')}' - path missing."
            )
            return

        if not self.drawerContent:
            logging.error("Cannot show drawer content: DrawerContentWidget is None.")
            return

        required_window_width = (
            self.leftPanel.width() + self.content_spacing + target_size.width()
        )
        required_window_height = max(self.leftPanel.height(), target_size.height())

        current_geom = self.geometry()
        if (
            current_geom.width() < required_window_width
            or current_geom.height() < required_window_height
        ):
            self.resize(required_window_width, required_window_height)
        elif (
            current_geom.width() > required_window_width
            or current_geom.height() > required_window_height
        ):
            self.resize(required_window_width, required_window_height)

        self.drawerContent.resize(target_size)
        self.drawerContent.move(
            self.leftPanel.width() + self.content_spacing, 0
        )
        self.drawerContent.update_content(folder_path)
        self.drawerContent.setVisible(True)
        self.drawerContent.raise_()

    def _on_hide_drawer_content(self) -> None:
        """响应 controller 的 hideDrawerContent 信号，隐藏内容区域。"""
        if self.drawerContent and self.drawerContent.isVisible():
            self.drawerContent.setVisible(False)
            self.resize(self.leftPanel.width(), self.leftPanel.height())

    def prompt_for_folder(self) -> Optional[str]:
        """Shows a dialog to select a folder and returns the path."""
        # Ensure the dialog opens on top of the main window
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", options=QFileDialog.Option.ShowDirsOnly
        )
        return folder if folder else None

    def get_drawer_content_size(self) -> QSize:
        """Returns the current size of the drawer content widget."""
        if self.drawerContent:
            return self.drawerContent.size()
        return QSize(0, 0)  # Return default/invalid size if no content widget

    def get_current_position(self) -> QPoint:
        """Returns the current top-left position of the main window."""
        return self.pos()

    def clear_list_selection(self) -> None:
        """Clears the current selection in the drawer list."""
        self.drawerList.clearSelection()
        # Optionally reset hover state if needed
        # self.drawerList.setCurrentItem(None)

    @Slot(float, float, float, float)
    def set_background_color(self, h: float, s: float, l: float, a: float) -> None:
        """Applies the background color to leftPanel and drawerContent using HSLA values (0.0-1.0)."""
        # 生成 HSLA 颜色字符串
        hsla_color = f"hsla({int(h * 359)}, {int(s * 100)}%, {int(l * 100)}%, {a:.2f})"

        # Define the style for both widgets using their object names
        # Apply border-radius for rounded corners if desired
        style = f"""
            QWidget#leftPanel {{
                background-color: {hsla_color};
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
                /* Add other specific styles for leftPanel if needed */
            }}
            /* Target the inner container of DrawerContentWidget using the custom property */
            QWidget[isDrawerContentContainer="true"] {{
                background-color: {hsla_color};
                border-radius: 5px; /* Apply to all corners or specific ones */
                /* Re-apply the border from style.qss to prevent it from being removed */
                border: 1px solid #424242;
            }}
        """
        # --- 新增逻辑 ---
        # 根据亮度 l (0.0-1.0) 决定字体颜色
        if l > 0.5:
            font_color = "#212121"  # 深色字体
        else:
            font_color = "#e0e0e0"  # 浅色字体
        # --- 结束新增逻辑 ---

        # --- 修改样式表生成 ---
        # 包含背景色和动态字体颜色
        style = f"""
            /* 背景色样式 */
            QWidget#leftPanel {{
                background-color: {hsla_color};
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
            }}
            QWidget[isDrawerContentContainer="true"] {{
                background-color: {hsla_color};
                border-radius: 5px;
                border: 1px solid #424242; /* 保留边框 */
            }}

            /* 动态字体颜色样式 */
            QWidget#leftPanel QLabel {{
                color: {font_color}; /* 设置左侧面板头部的字体颜色 */
            }}
            DrawerContentWidget QLabel {{
                color: {font_color}; /* 设置内容区域标签的字体颜色 */
            }}
            QWidget#leftPanel QLabel {{
                color: {font_color}; /* 设置左侧面板头部的字体颜色 */
            }}
            DrawerListWidget::item {{
                color: {font_color};
                /* 注意：这里只设置颜色，其他样式如 padding, border-bottom 应由 style.qss 提供 */
                /* 可能需要确保这里的优先级正确 */
            }}
            DrawerContentWidget QLabel {{
                color: {font_color};
                /* background-color: transparent; /* 确保背景透明 */ */
            }}
        """
        # --- 结束修改样式表生成 ---
        # Qt will propagate the styles to the children based on the selectors.
        self.setStyleSheet(style)
        # Note: Applying directly to self.leftPanel.setStyleSheet and self.drawerContent.setStyleSheet
        # might also work but applying to the parent is often preferred for managing styles.

    def apply_initial_background(self) -> None:
        """Loads initial background color (CSS format) from settings, converts it, and applies it."""
        if self.controller and self.controller.settings_manager:
            # Get color in CSS format (H:0-359, S:0-100, L:0-100, A:0.0-1.0)
            h_css, s_css, l_css, a_float = (
                self.controller.settings_manager.get_background_color_hsla()
            )
            # Convert to 0.0-1.0 floats for the set_background_color slot
            h_float = h_css / 359.0
            s_float = s_css / 100.0
            l_float = l_css / 100.0
            # Ensure floats are valid
            h_float = max(0.0, min(1.0, h_float))
            s_float = max(0.0, min(1.0, s_float))
            l_float = max(0.0, min(1.0, l_float))
            a_float = max(0.0, min(1.0, a_float))
            # Call the slot with 0.0-1.0 floats
            self.set_background_color(h_float, s_float, l_float, a_float)
        else:
            logging.warning(
                "Controller or SettingsManager not ready for initial background application."
            )

    # --- Tray Icon Methods ---

    def _create_tray_icon(self) -> None:
        """Creates the system tray icon and its context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = "asset/drawer.icon.4.ico"  # Consider making path configurable
        icon = QIcon(icon_path)
        if icon.isNull():
            logging.warning(f"Tray icon file '{icon_path}' not found or invalid.")
            # Fallback icon or handle error might be needed
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("图标抽屉管理器")

        # 创建上下文菜单
        self.tray_menu = QMenu(self)
        self.tray_menu.setStyleSheet(
            "background-color: rgba(50, 50, 50, 200); border: 1px solid #424242;"
        )  # 设置更深的背景色和边框
        self.tray_menu = QMenu(self)
        show_hide_action = QAction("显示/隐藏", self)
        quit_action = QAction("退出", self)

        # Connect actions
        show_hide_action.triggered.connect(self._toggle_window_visibility)
        quit_action.triggered.connect(self._quit_application)

        # Add actions to menu
        self.tray_menu.addAction(show_hide_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)

        # Set menu to tray icon
        self.tray_icon.setContextMenu(self.tray_menu)

        # Connect tray icon activation signal
        self.tray_icon.activated.connect(self._handle_tray_activated)

        # Show the tray icon
        self.tray_icon.show()

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handles activation of the system tray icon."""
        # Show/hide window on left click
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window_visibility()
        # Context menu is handled automatically on right-click

    def _toggle_window_visibility(self) -> None:
        """Toggles the visibility of the main window."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()  # Bring to front
            self.raise_()  # Ensure it's on top

    def _quit_application(self) -> None:
        """Cleans up and quits the application."""
        self.tray_icon.hide()  # Hide tray icon before quitting
        # Add any other cleanup needed here (e.g., saving settings explicitly)
        QCoreApplication.quit()

    # --- Window Resize Logic ---

    def _handle_content_size_changed(self, new_content_size: QSize) -> None:
        """Handles the sizeChanged signal from DrawerContentWidget."""
        # Check if drawerContent exists and is visible
        if not self.drawerContent or not self.drawerContent.isVisible():
            return  # Don't resize if the content widget isn't visible or doesn't exist

        # Calculate required window size based on the new content size
        required_window_width = (
            self.leftPanel.width() + self.content_spacing + new_content_size.width()
        )
        required_window_height = max(self.leftPanel.height(), new_content_size.height())

        # Resize the main window
        self.resize(required_window_width, required_window_height)

        # Ensure content widget is still positioned correctly after potential window resize
        # (might not be strictly necessary if layout handles it, but good for robustness)
        if self.drawerContent:
            self.drawerContent.move(self.leftPanel.width() + self.content_spacing, 0)

    # --- Event Overrides ---

    def moveEvent(self, event: QMoveEvent) -> None:
        """Overrides the move event to emit the windowMoved signal."""
        super().moveEvent(event)
        # Emit signal only if the controller exists (to avoid issues during init)
        if hasattr(self, "controller") and self.controller:
            self.windowMoved.emit(self.pos())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Overrides the close event to hide the window instead of quitting."""
        # Hide the window and ignore the event (preventing application quit)
        self.hide()
        event.ignore()

    # --- Settings Dialog ---

    def show_settings_dialog(self) -> None:
        """Shows the settings dialog."""
        if not self.controller or not self.controller.settings_manager:
            logging.error(
                "Controller or SettingsManager not available for settings dialog."
            )
            return

        dialog = SettingsDialog(self.controller.settings_manager, self)

        # Connect signals from the dialog
        # 1. Preview signal connected directly to main window's background setter
        dialog.backgroundPreviewRequested.connect(self.set_background_color)
        # 2. Apply/Save signals connected to controller's handlers
        dialog.backgroundApplied.connect(self.controller.handle_background_applied)
        dialog.startupToggled.connect(self.controller.handle_startup_toggled)
        # 3. Connect Quit signal
        # Check if instance exists before connecting quit
        app_instance = QApplication.instance()
        if app_instance:
            dialog.quitApplicationRequested.connect(app_instance.quit)
        else:
            logging.error(
                "QApplication instance not found when connecting quit signal."
            )

        dialog.exec()

        # Disconnect signals after dialog is closed to avoid potential issues
        # It's generally good practice, though might not be strictly necessary
        # if the dialog is garbage collected properly.
        try:
            dialog.backgroundPreviewRequested.disconnect(self.set_background_color)
            dialog.backgroundApplied.disconnect(
                self.controller.handle_background_applied
            )
            dialog.startupToggled.disconnect(self.controller.handle_startup_toggled)
            # Disconnect Quit signal
            app_instance = QApplication.instance()
            if app_instance:
                dialog.quitApplicationRequested.disconnect(app_instance.quit)
        except RuntimeError:
            # Signals might already be disconnected if dialog was closed abruptly
            pass

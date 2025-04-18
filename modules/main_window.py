import logging
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
    QApplication,
)
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QCoreApplication, Slot
from PySide6.QtGui import QMoveEvent, QAction, QIcon, QCloseEvent

from modules.settings_manager import DrawerDict
from modules.list import DrawerListWidget
from modules.drawer_ui import DrawerContentWidget
# from modules.drawer_utils import IDrawerContent
from modules.window_drag_area import DragArea
from modules.settings_dialog import SettingsDialog

if TYPE_CHECKING:
    from modules.controller import AppController
from modules.controller import USER_ROLE


class MainWindow(QMainWindow):
    windowMoved = Signal(QPoint)

    def __init__(self) -> None:
        super().__init__()
        self.controller: Optional["AppController"] = None
        self._setup_window_properties()
        self._setup_ui()

        from modules.controller import AppController

        self.controller = AppController(self)

        if not self.controller:
            logging.critical(
                "Controller failed to initialize before creating DrawerContentWidget!"
            )
            self.drawerContent = None
        else:
            self.drawerContent = DrawerContentWidget(
                self.controller, self._central_widget_container
            )
            if self.drawerContent is not None:
                self.drawerContent.setObjectName("drawerContent")
                self.drawerContent.setVisible(False)
                self.drawerContent.setMinimumSize(300, 200)
                self.drawerContent.move(
                    self.leftPanel.width() + self.content_spacing, 0
                )

        if self.controller:
            self.controller.showDrawerContent.connect(self._on_show_drawer_content)
            self.controller.hideDrawerContent.connect(self._on_hide_drawer_content)
            self.controller.updateDrawerContent.connect(self._on_update_drawer_content)

        self._connect_signals()
        self._create_tray_icon()

    def _setup_window_properties(self) -> None:
        self.setWindowTitle("iconDrawer")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setObjectName("mainWindow")

    def _setup_ui(self) -> None:
        self._central_widget_container = QWidget()
        self._central_widget_container.setObjectName("centralWidgetContainer")
        self.setCentralWidget(self._central_widget_container)

        mainLayout = QHBoxLayout(self._central_widget_container)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        self._setup_left_panel(mainLayout)
        self._setup_right_panel()

        mainLayout.addStretch(1)

    def _setup_left_panel(self, mainLayout: QHBoxLayout) -> None:
        self.leftPanel = QWidget()
        self.leftPanel.setObjectName("leftPanel")
        self.leftPanel.setFixedSize(210, 300)

        leftLayout = QVBoxLayout(self.leftPanel)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(0)

        self.dragArea = DragArea(self.leftPanel)
        self.dragArea.setObjectName("dragArea")
        leftLayout.addWidget(self.dragArea)

        self.drawerList = DrawerListWidget(self.leftPanel)
        self.drawerList.setObjectName("drawerList")
        self.drawerList.setFixedSize(210, 240)
        leftLayout.addWidget(self.drawerList)

        self.addButton = QPushButton("Add Drawer", self.leftPanel)
        self.addButton.setObjectName("addButton")
        leftLayout.addWidget(self.addButton)

        mainLayout.addWidget(self.leftPanel, 0, alignment=Qt.AlignmentFlag.AlignTop)

    def _setup_right_panel(self) -> None:
        self.drawerContent: Optional[DrawerContentWidget] = None
        self.content_spacing = 5

    def _connect_signals(self) -> None:
        if not self.controller:
            logging.error("Controller not initialized during signal connection.")
            return

        self.addButton.clicked.connect(self.controller.add_new_drawer)
        self.drawerList.itemSelected.connect(self.controller.handle_item_selected)
        self.drawerList.selectionCleared.connect(
            self.controller.handle_selection_cleared
        )
        self.dragArea.settingsRequested.connect(
            self.controller.handle_settings_requested
        )
        self.dragArea.dragFinished.connect(self.controller.handle_window_drag_finished)

        if self.drawerContent:
            self.drawerContent.closeRequested.connect(
                self.controller.handle_content_close_requested
            )
            self.drawerContent.resizeFinished.connect(
                self.controller.handle_content_resize_finished
            )
            self.drawerContent.sizeChanged.connect(self._handle_content_size_changed)
        else:
            logging.error("DrawerContentWidget is None, cannot connect its signals.")

        self.windowMoved.connect(self.controller.update_window_position)
        self.apply_initial_background()

    def populate_drawer_list(self, drawers: List[DrawerDict]) -> None:
        self.drawerList.clear()
        for drawer_data in drawers:
            name = drawer_data.get("name", "Unnamed Drawer")
            item = QListWidgetItem(name)
            item.setData(USER_ROLE, drawer_data)
            self.drawerList.addItem(item)

    def add_drawer_item(self, drawer: DrawerDict) -> None:
        name = drawer.get("name", "Unnamed Drawer")
        item = QListWidgetItem(name)
        item.setData(USER_ROLE, drawer)
        self.drawerList.addItem(item)

    def set_initial_position(self, pos: QPoint) -> None:
        self.move(pos)

    def _on_show_drawer_content(
        self, drawer_data: DrawerDict, target_size: QSize
    ) -> None:
        folder_path = drawer_data.get("path")
        if not folder_path:
            logging.error(
                f"Cannot show content for drawer '{drawer_data.get('name')}' - path missing."
            )
            return
        if not self.drawerContent:
            logging.error("Cannot show drawer content: DrawerContentWidget is None.")
            return

        required_width = (
            self.leftPanel.width() + self.content_spacing + target_size.width()
        )
        required_height = max(self.leftPanel.height(), target_size.height())

        current_geom = self.geometry()
        if (
            current_geom.width() != required_width
            or current_geom.height() != required_height
        ):
            self.resize(required_width, required_height)

        self.drawerContent.resize(target_size)
        self.drawerContent.move(self.leftPanel.width() + self.content_spacing, 0)
        self.drawerContent.update_content(folder_path)
        self.drawerContent.setVisible(True)
        self.drawerContent.raise_()

    def _on_hide_drawer_content(self) -> None:
        if self.drawerContent and self.drawerContent.isVisible():
            self.drawerContent.setVisible(False)
            self.resize(self.leftPanel.width(), self.leftPanel.height())

    def _on_update_drawer_content(self, path: str) -> None:
        if self.drawerContent:
            self.drawerContent.update_content(path)

    def prompt_for_folder(self) -> Optional[str]:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", options=QFileDialog.Option.ShowDirsOnly
        )
        return folder if folder else None

    def get_drawer_content_size(self) -> QSize:
        if self.drawerContent:
            return self.drawerContent.size()
        return QSize(0, 0)

    def get_current_position(self) -> QPoint:
        return self.pos()

    def clear_list_selection(self) -> None:
        self.drawerList.clearSelection()

    @Slot(float, float, float, float)
    def set_background_color(
        self, h: float, s: float, l_float: float, a: float
    ) -> None:
        hsla_color = (
            f"hsla({int(h * 359)}, {int(s * 100)}%, {int(l_float * 100)}%, {a:.2f})"
        )
        style = f"""
            QWidget#leftPanel {{
                background-color: {hsla_color};
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
            }}
            QWidget[isDrawerContentContainer="true"] {{
                background-color: {hsla_color};
                border-radius: 5px;
                border: 1px solid #424242;
            }}
            QWidget#leftPanel QLabel, DrawerContentWidget QLabel, DrawerListWidget::item {{
                color: {"#212121" if l_float > 0.5 else "#e0e0e0"};
            }}
        """
        self.setStyleSheet(style)

    def apply_initial_background(self) -> None:
        if self.controller and self.controller.settings_manager:
            h_css, s_css, l_css, a_float = (
                self.controller.settings_manager.get_background_color_hsla()
            )
            h_float = max(0.0, min(1.0, h_css / 359.0))
            s_float = max(0.0, min(1.0, s_css / 100.0))
            l_float = max(0.0, min(1.0, l_css / 100.0))
            a_float = max(0.0, min(1.0, a_float))
            self.set_background_color(h_float, s_float, l_float, a_float)
        else:
            logging.warning(
                "Controller or SettingsManager not ready for initial background application."
            )

    def _create_tray_icon(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = "asset/drawer.icon.4.ico"
        icon = QIcon(icon_path)
        if icon.isNull():
            logging.warning(f"Tray icon file '{icon_path}' not found or invalid.")
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("图标抽屉管理器")

        self.tray_menu = QMenu(self)
        self.tray_menu.setObjectName("trayMenu")
        self.tray_menu.setStyleSheet(
            "background-color: rgba(50, 50, 50, 200); border: 1px solid #424242;"
        )
        show_hide_action = QAction("显示/隐藏", self)
        quit_action = QAction("退出", self)

        show_hide_action.triggered.connect(self._toggle_window_visibility)
        quit_action.triggered.connect(self._quit_application)

        self.tray_menu.addAction(show_hide_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window_visibility()

    def _toggle_window_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.raise_()

    def _quit_application(self) -> None:
        self.tray_icon.hide()
        QCoreApplication.quit()

    def _handle_content_size_changed(self, new_content_size: QSize) -> None:
        if not self.drawerContent or not self.drawerContent.isVisible():
            return

        required_width = (
            self.leftPanel.width() + self.content_spacing + new_content_size.width()
        )
        required_height = max(self.leftPanel.height(), new_content_size.height())
        self.resize(required_width, required_height)

        if self.drawerContent:
            self.drawerContent.move(self.leftPanel.width() + self.content_spacing, 0)

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        if hasattr(self, "controller") and self.controller:
            self.windowMoved.emit(self.pos())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()

    def show_settings_dialog(self) -> None:
        if not self.controller or not self.controller.settings_manager:
            logging.error(
                "Controller or SettingsManager not available for settings dialog."
            )
            return

        dialog = SettingsDialog(self.controller.settings_manager, self)
        dialog.backgroundPreviewRequested.connect(self.set_background_color)
        dialog.backgroundApplied.connect(self.controller.handle_background_applied)
        dialog.startupToggled.connect(self.controller.handle_startup_toggled)

        app_instance = QApplication.instance()
        if app_instance:
            dialog.quitApplicationRequested.connect(app_instance.quit)
        else:
            logging.error(
                "QApplication instance not found when connecting quit signal."
            )

        dialog.exec()

        try:
            dialog.backgroundPreviewRequested.disconnect(self.set_background_color)
            dialog.backgroundApplied.disconnect(
                self.controller.handle_background_applied
            )
            dialog.startupToggled.disconnect(self.controller.handle_startup_toggled)
            if app_instance:
                dialog.quitApplicationRequested.disconnect(app_instance.quit)
        except RuntimeError:
            pass

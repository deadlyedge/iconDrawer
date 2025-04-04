from typing import List, Optional, TYPE_CHECKING, Tuple
from PySide6.QtCore import QObject, QPoint, QSize, Slot # Import Slot
from PySide6.QtWidgets import QListWidgetItem, QMessageBox # Added QMessageBox
from modules.settings_manager import SettingsManager, DrawerDict
from pathlib import Path
import logging # Import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use TYPE_CHECKING to avoid circular imports for type hints
if TYPE_CHECKING:
    from modules.main_window import MainWindow

# Define USER_ROLE constant for item data
USER_ROLE: int = 32 # Qt.ItemDataRole.UserRole starts at 32

class AppController(QObject):
    """
    Manages the application's state and logic, acting as a controller
    between the view (MainWindow) and the data (ConfigManager).
    """
    def __init__(self, main_view: 'MainWindow', parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._main_view = main_view
        # Initialize SettingsManager instance for easier access
        self.settings_manager = SettingsManager()
        self._drawers_data: List[DrawerDict] = []
        self._window_position: Optional[QPoint] = None
        self._background_color_hsla: Tuple[float, float, float, float] = self.settings_manager.DEFAULT_BG_COLOR_HSLA
        self._start_with_windows: bool = self.settings_manager.DEFAULT_START_WITH_WINDOWS
        self._locked: bool = False
        self._locked_item_data: Optional[DrawerDict] = None

        self._load_initial_data()

    # --- Data Management ---

    def _load_initial_data(self) -> None:
        """Loads initial settings and updates the view."""
        # Load all settings
        drawers, window_pos, bg_color, start_flag = self.settings_manager.load_settings()
        self._drawers_data = drawers
        self._window_position = window_pos
        self._background_color_hsla = bg_color
        self._start_with_windows = start_flag
        # logging.info(f"Loaded initial settings: Pos={window_pos}, BG={bg_color}, Startup={start_flag}")

        # Update view components
        self._main_view.populate_drawer_list(self._drawers_data)
        if self._window_position:
            self._main_view.set_initial_position(self._window_position)
        # Initial background is applied by MainWindow itself after controller is ready

    def save_settings(self) -> None:
        """Saves the current application state (drawers and window position)."""
        # Ensure the latest window position is captured before saving
        current_pos = self._main_view.get_current_position()
        if current_pos:
            self._window_position = current_pos
        # logging.info(f"Saving data: Drawers={self._drawers_data}, Pos={self._window_position}, BG={self._background_color_hsla}, Startup={self._start_with_windows}")
        self.settings_manager.save_settings(
            drawers=self._drawers_data,
            window_position=self._window_position,
            background_color_hsla=self._background_color_hsla,
            start_with_windows=self._start_with_windows
        )
        logging.info("Settings saved.") # Keep critical log

    # --- Drawer Operations ---

    def add_new_drawer(self) -> None:
        """Handles the request to add a new drawer."""
        folder_path_str = self._main_view.prompt_for_folder()
        if folder_path_str:
            folder_path = Path(folder_path_str)
            if folder_path.is_dir():
                name = folder_path.name
                # Check for duplicate names or paths if necessary
                is_duplicate = any(d.get("path") == folder_path_str for d in self._drawers_data)
                if is_duplicate:
                    QMessageBox.warning(self._main_view, "重复抽屉", f"路径 '{folder_path_str}' 已经被添加。")
                    return

                new_drawer_data: DrawerDict = {"name": name, "path": folder_path_str} # Store path as string initially
                self._drawers_data.append(new_drawer_data)
                self._main_view.add_drawer_item(new_drawer_data)
                self.save_settings()
            else:
                # Handle invalid folder selection
                logging.error(f"Selected path is not a valid directory: {folder_path_str}")
                QMessageBox.warning(self._main_view, "无效路径", f"选择的路径不是一个有效的文件夹:\n{folder_path_str}")

    def update_drawer_size(self, drawer_name: str, new_size: QSize) -> None:
        """Updates the size information for a specific drawer."""
        updated = False
        for drawer in self._drawers_data:
            if drawer.get("name") == drawer_name:
                # Only update if the size actually changed to avoid unnecessary saves
                if drawer.get("size") != new_size:
                    drawer["size"] = new_size # Directly update the QSize object
                    updated = True
                    # logging.info(f"Updating size for drawer '{drawer_name}' to {new_size}") # DEBUG removed
                break # Found the drawer, no need to continue loop
        if updated:
            self.save_settings()
        # else:
            # logging.warning(f"Could not find drawer '{drawer_name}' to update size.") # Warning removed

    def update_window_position(self, pos: QPoint) -> None:
        """Updates the stored window position."""
        # Only update if position actually changed
        if self._window_position != pos:
            self._window_position = pos
            # Debounce saving or save on specific events like dragFinished
            # self.save_settings() # Avoid saving on every move event

    # --- Slot Handlers for View Signals ---

    def handle_item_selected(self, item: QListWidgetItem) -> None:
        """
        Handles drawer list item selection and locking logic.
        This method determines the target size, checks the lock state,
        and updates the view accordingly.
        """
        # --- Step 0: Basic Validation ---
        drawer_data = item.data(USER_ROLE)
        if not isinstance(drawer_data, dict):
            logging.error(f"Invalid data in selected item '{item.text()}'.")
            return

        folder_path_str = drawer_data.get("path")
        if not folder_path_str or not Path(folder_path_str).is_dir():
             logging.error(f"Invalid or non-existent path for item '{item.text()}': {folder_path_str}")
             QMessageBox.warning(self._main_view, "路径无效", f"抽屉 '{item.text()}' 的路径无效或不存在:\n{folder_path_str}\n请考虑移除此抽屉。")
             return

        # --- Step 1: Get the LATEST size information for the selected drawer ---
        # The item data might be stale, so always fetch the current config from _drawers_data
        current_drawer_config = None
        drawer_name_to_find = drawer_data.get("name")
        if drawer_name_to_find:
            for config in self._drawers_data:
                if config.get("name") == drawer_name_to_find:
                    current_drawer_config = config
                    break

        # Determine the target size for the content widget
        if current_drawer_config:
            target_content_size = current_drawer_config.get("size")
            # Use default size if not found or invalid in the current config
            if not isinstance(target_content_size, QSize):
                target_content_size = QSize(640, 480) # Default size
            # Update the item's data to reflect the latest config (optional but good practice)
            item.setData(USER_ROLE, current_drawer_config)
        else:
            # Fallback: If somehow the drawer isn't in _drawers_data, use item data or default
            logging.warning(f"Could not find '{drawer_name_to_find}' in current config, using item data size.")
            target_content_size = drawer_data.get("size")
            if not isinstance(target_content_size, QSize):
                target_content_size = QSize(640, 480) # Default size

        # --- Step 2: Handle Locking Logic ---
        if self._locked:
            # If already locked, check if the same item was clicked again
            # Use the most up-to-date config for comparison
            compare_data = current_drawer_config if current_drawer_config else drawer_data
            if compare_data == self._locked_item_data:
                # Case A: Clicked the currently locked item -> Unlock and hide
                self._locked = False
                self._locked_item_data = None
                self._main_view.hide_drawer_content()
                # logging.info("Drawer unlocked")
            else:
                # Case B: Clicked a different item while locked -> Switch content
                # --- Save size of the OLD drawer before switching ---
                if self._locked_item_data:
                    old_drawer_name = self._locked_item_data.get("name")
                    if old_drawer_name:
                        old_size = self._main_view.get_drawer_content_size() # Get size *before* content updates
                        self.update_drawer_size(old_drawer_name, old_size) # Save if changed
                # --- Switch to the new item ---
                self._locked_item_data = current_drawer_config if current_drawer_config else drawer_data # Store the latest config
                self._main_view.show_drawer_content(self._locked_item_data, target_content_size)
                # logging.info(f"Drawer remains locked, content updated to: {self._locked_item_data.get('name')}")
        else:
            # Case C: Not locked -> Lock and show the selected item
            self._locked = True
            self._locked_item_data = current_drawer_config if current_drawer_config else drawer_data # Store the latest config
            self._main_view.show_drawer_content(self._locked_item_data, target_content_size)
            # logging.info(f"Drawer locked on: {self._locked_item_data.get('name')}")


    def handle_selection_cleared(self) -> None:
        """Hides content view if not locked."""
        # If the list selection is cleared (e.g., mouse leaves the list)
        # only hide the content if it's not locked.
        if not self._locked:
            # Size saving is handled by resize/drag finish signals, no need here.
            self._main_view.hide_drawer_content()
            # logging.info("Drawer content cleared (selection lost, unlocked)")
        # If it IS locked, selection change doesn't hide it.

    def handle_content_close_requested(self) -> None:
        """Handles the close request from the content widget."""
        # --- Save size before closing (as a potential fallback) ---
        if self._locked and self._locked_item_data:
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                current_size = self._main_view.get_drawer_content_size()
                self.update_drawer_size(drawer_name, current_size) # Save if changed

        # --- Actual closing logic ---
        self._locked = False
        self._locked_item_data = None
        self._main_view.hide_drawer_content()
        self._main_view.clear_list_selection() # Ensure list selection is also cleared
        # logging.info("Drawer content closed and unlocked")

    def handle_content_resize_finished(self) -> None:
        """Handles the resize finished signal from the content widget."""
        # Save the size of the locked drawer when resizing via grip finishes.
        if self._locked and self._locked_item_data:
            current_size = self._main_view.get_drawer_content_size()
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                self.update_drawer_size(drawer_name, current_size) # Save if changed
            # else:
                 # logging.warning("Cannot save size on resize finish, locked item has no name.")

    def handle_window_drag_finished(self) -> None:
        """Saves settings when window dragging finishes."""
        # This signal implies both window position and potentially drawer size might need saving.
        # 1. Update window position in memory (save_settings will handle the rest)
        current_pos = self._main_view.get_current_position()
        if current_pos and self._window_position != current_pos:
             self._window_position = current_pos # Update internal state

        # 2. Update size of the locked drawer in memory if it's visible
        if self._locked and self._locked_item_data:
            current_size = self._main_view.get_drawer_content_size()
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                # Find and update the size directly in _drawers_data
                # This avoids calling update_drawer_size which would trigger another save
                for drawer in self._drawers_data:
                    if drawer.get("name") == drawer_name:
                        if drawer.get("size") != current_size:
                            drawer["size"] = current_size
                            # logging.info(f"Drawer '{drawer_name}' size updated in memory to {current_size} on window drag finish.")
                        break

        # 3. Save settings (includes potentially updated position and size)
        self.save_settings()
        # logging.info("Window drag finished, settings saved.")


    def handle_settings_requested(self) -> None:
        """Handles the request to open the settings dialog."""
        self._main_view.show_settings_dialog()

    @Slot(float, float, float, float)
    def handle_background_applied(self, h: float, s: float, l: float, a: float) -> None:
        """Handles the final background color applied from settings dialog."""
        new_color = (h, s, l, a)
        if self._background_color_hsla != new_color:
            self._background_color_hsla = new_color
            self.save_settings() # Save all settings when background is confirmed
            logging.info(f"Background color setting updated to: {new_color}")
            # The main window background is already updated via the preview signal

    @Slot(bool)
    def handle_startup_toggled(self, enabled: bool) -> None:
        """Handles the startup toggle from settings dialog."""
        if self._start_with_windows != enabled:
            self._start_with_windows = enabled
            self.save_settings() # Save all settings when startup flag changes
            logging.info(f"Start with Windows setting updated to: {enabled}")
            # TODO: Implement the actual logic to add/remove from startup
            # This usually involves platform-specific code (e.g., Windows Registry)
            self._update_startup_registry(enabled) # Placeholder for registry logic

    def _update_startup_registry(self, enable: bool) -> None:
        """Placeholder for platform-specific startup logic (e.g., Windows Registry)."""
        # This needs to be implemented based on the target OS.
        # For Windows, it involves using the 'winreg' module.
        # For macOS, it involves creating/deleting a .plist file in ~/Library/LaunchAgents.
        # For Linux, it involves creating/deleting a .desktop file in ~/.config/autostart.
        if enable:
            logging.info("Placeholder: Adding application to system startup.")
            # Example (Windows - requires 'pip install pywin32' potentially):
            # try:
            #     import winreg
            #     import sys
            #     key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            #     app_name = "IconDrawer" # Or get from application info
            #     app_path = sys.executable # Path to the python interpreter running the script
            #     script_path = Path(__file__).resolve().parents[1] / "main.py" # Adjust path to your main script
            #     command = f'"{app_path}" "{script_path}"'
            #
            #     with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
            #         winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
            #     logging.info(f"Added '{app_name}' to startup registry.")
            # except ImportError:
            #     logging.error("Could not import winreg. Startup setting not applied (Windows). Install pywin32.")
            # except Exception as e:
            #     logging.error(f"Failed to add to startup registry: {e}")
            pass
        else:
            logging.info("Placeholder: Removing application from system startup.")
            # Example (Windows):
            # try:
            #     import winreg
            #     key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            #     app_name = "IconDrawer"
            #     with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
            #         winreg.DeleteValue(key, app_name)
            #     logging.info(f"Removed '{app_name}' from startup registry.")
            # except FileNotFoundError:
            #      logging.info(f"'{app_name}' not found in startup registry (already removed?).")
            # except ImportError:
            #     logging.error("Could not import winreg. Startup setting not applied (Windows). Install pywin32.")
            # except Exception as e:
            #     logging.error(f"Failed to remove from startup registry: {e}")
            pass
        # Add similar blocks for macOS and Linux if needed

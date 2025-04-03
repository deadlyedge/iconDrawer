from typing import List, Optional, TYPE_CHECKING
from PySide6.QtCore import QObject, QPoint, QSize
from PySide6.QtWidgets import QListWidgetItem
from modules.config_manager import ConfigManager, DrawerDict
from pathlib import Path

# Use TYPE_CHECKING to avoid circular imports for type hints
if TYPE_CHECKING:
    from modules.main_window import MainWindow

USER_ROLE: int = 32 # Assuming this is defined globally or passed appropriately

class AppController(QObject):
    """
    Manages the application's state and logic, acting as a controller
    between the view (MainWindow) and the data (ConfigManager).
    """
    def __init__(self, main_view: 'MainWindow', parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._main_view = main_view
        self._drawers_data: List[DrawerDict] = []
        self._window_position: Optional[QPoint] = None
        self._locked: bool = False
        self._locked_item_data: Optional[DrawerDict] = None

        self._load_initial_data()

    # --- Data Management ---

    def _load_initial_data(self) -> None:
        """Loads initial configuration and updates the view."""
        drawers, window_position = ConfigManager.load_config()
        self._drawers_data = drawers
        self._window_position = window_position
        print(f"[_load_initial_data] Loaded drawers data: {self._drawers_data}") # DEBUG

        self._main_view.populate_drawer_list(self._drawers_data)
        if self._window_position:
            self._main_view.set_initial_position(self._window_position)

    def save_configuration(self) -> None:
        """Saves the current application state (drawers and window position)."""
        # Ensure the latest window position is captured before saving
        current_pos = self._main_view.get_current_position()
        if current_pos:
            self._window_position = current_pos
        print(f"[save_configuration] Saving data: {self._drawers_data}") # DEBUG
        ConfigManager.save_config(self._drawers_data, self._window_position)
        print("Configuration saved.") # Optional: Confirmation log

    # --- Drawer Operations ---

    def add_new_drawer(self) -> None:
        """Handles the request to add a new drawer."""
        folder_path_str = self._main_view.prompt_for_folder()
        if folder_path_str:
            folder_path = Path(folder_path_str)
            if folder_path.is_dir():
                name = folder_path.name
                # Check for duplicate names or paths if necessary
                # ... (add duplicate check logic if needed) ...
                new_drawer_data: DrawerDict = {"name": name, "path": folder_path_str} # Store path as string initially
                self._drawers_data.append(new_drawer_data)
                self._main_view.add_drawer_item(new_drawer_data)
                self.save_configuration()
            else:
                # Handle invalid folder selection
                print(f"Error: Selected path is not a valid directory: {folder_path_str}")
                # Optionally show a message box via main_view

    def update_drawer_size(self, drawer_name: str, new_size: QSize) -> None:
        """Updates the size information for a specific drawer."""
        updated = False
        for drawer in self._drawers_data:
            if drawer.get("name") == drawer_name:
                drawer["size"] = new_size # Directly update the QSize object
                drawer["size"] = new_size # Directly update the QSize object
                updated = True
                break
        if updated:
            print(f"[update_drawer_size] Attempting to save size {new_size} for drawer '{drawer_name}'") # DEBUG
            self.save_configuration()
        else:
            print(f"Warning: Could not find drawer '{drawer_name}' to update size.")

    def update_window_position(self, pos: QPoint) -> None:
        """Updates the stored window position."""
        self._window_position = pos
        # Debounce saving or save on specific events like dragFinished
        # self.save_configuration() # Avoid saving on every move event

    # --- Slot Handlers for View Signals ---

    def handle_item_selected(self, item: QListWidgetItem) -> None:
        """Handles drawer list item selection and locking logic."""
        drawer_data = item.data(USER_ROLE)
        if not isinstance(drawer_data, dict):
            print(f"Error: Invalid data in selected item '{item.text()}'.")
            return

        folder_path_str = drawer_data.get("path")
        if not folder_path_str or not Path(folder_path_str).is_dir():
             print(f"Error: Invalid or non-existent path for item '{item.text()}': {folder_path_str}")
             print(f"Error: Invalid or non-existent path for item '{item.text()}': {folder_path_str}")
             # Optionally remove the item or notify the user
             return

        # --- Get the LATEST size information ---
        # Find the corresponding entry in self._drawers_data to get the most up-to-date size
        current_drawer_config = None
        drawer_name_to_find = drawer_data.get("name")
        if drawer_name_to_find:
            for config in self._drawers_data:
                if config.get("name") == drawer_name_to_find:
                    current_drawer_config = config
                    break

        if current_drawer_config:
            target_content_size = current_drawer_config.get("size")
            if not isinstance(target_content_size, QSize):
                target_content_size = QSize(640, 480) # Default if size is missing/invalid in current config
            # Update the item data as well, though it's less critical now
            item.setData(USER_ROLE, current_drawer_config)
        else:
            # Fallback to item data or default if not found in self._drawers_data (should not happen ideally)
            print(f"Warning: Could not find '{drawer_name_to_find}' in current config, using item data size.")
            target_content_size = drawer_data.get("size")
            if not isinstance(target_content_size, QSize):
                target_content_size = QSize(640, 480) # Default size
            print(f"[handle_item_selected] Determined target size for '{drawer_name_to_find}': {target_content_size}") # DEBUG

        # --- Locking Logic ---
        if self._locked:
            # Use current_drawer_config if available for comparison, otherwise fallback to drawer_data
            compare_data = current_drawer_config if current_drawer_config else drawer_data
            if compare_data == self._locked_item_data:
                # Unlock if the locked item is clicked again
                self._locked = False
                self._locked_item_data = None
                self._main_view.hide_drawer_content()
                print("Drawer unlocked")
            else:
                # --- Save size of the OLD drawer before switching ---
                if self._locked_item_data:
                    old_drawer_name = self._locked_item_data.get("name")
                    if old_drawer_name:
                        old_size = self._main_view.get_drawer_content_size() # Get size before content updates
                        print(f"[handle_item_selected] Saving size {old_size} for OLD drawer '{old_drawer_name}' before switching.") # DEBUG
                        self.update_drawer_size(old_drawer_name, old_size)
                # --- Switch locked item ---
                self._locked_item_data = current_drawer_config if current_drawer_config else drawer_data
                # Pass the most current config data and the determined target size
                self._main_view.show_drawer_content(self._locked_item_data, target_content_size)
                print(f"Drawer remains locked, content updated to: {self._locked_item_data.get('name')}")
        else:
            # Lock and show (use the most current config data)
            self._locked = True
            self._locked_item_data = current_drawer_config if current_drawer_config else drawer_data
            # Pass the most current config data and the determined target size
            self._main_view.show_drawer_content(self._locked_item_data, target_content_size)
            print(f"Drawer locked on: {self._locked_item_data.get('name')}")


    def handle_selection_cleared(self) -> None:
        """Hides content view if not locked, saving size if it was locked."""
        if not self._locked:
            # --- Save size if an item WAS locked before clearing selection ---
            if self._locked_item_data:
                 drawer_name = self._locked_item_data.get("name")
                 if drawer_name:
                     current_size = self._main_view.get_drawer_content_size()
                     print(f"[handle_selection_cleared] Saving size {current_size} for previously locked drawer '{drawer_name}'.") # DEBUG
                     self.update_drawer_size(drawer_name, current_size)
                 self._locked_item_data = None # Clear locked data since selection is gone

            self._main_view.hide_drawer_content()
            print("Drawer content cleared (selection lost, unlocked)")
        # If it IS locked, selection change doesn't hide it, so no action needed here.

    def handle_content_close_requested(self) -> None:
        """Handles the close request from the content widget."""
        # --- Save size before closing ---
        if self._locked and self._locked_item_data:
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                current_size = self._main_view.get_drawer_content_size()
                print(f"[handle_content_close_requested] Saving size {current_size} for closing drawer '{drawer_name}'.") # DEBUG
                self.update_drawer_size(drawer_name, current_size)

        # --- Original closing logic ---
        self._locked = False
        self._locked_item_data = None
        self._main_view.hide_drawer_content()
        # Also clear selection in the list view
        self._main_view.clear_list_selection()
        print("Drawer content closed and unlocked")

    def handle_content_resize_finished(self) -> None:
        """Handles the resize finished signal from the content widget."""
        if self._locked and self._locked_item_data:
            current_size = self._main_view.get_drawer_content_size()
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                print(f"[handle_content_resize_finished] Detected size {current_size} for '{drawer_name}'") # DEBUG
                self.update_drawer_size(drawer_name, current_size)
                # print(f"Resize finished for '{drawer_name}', saved size: {current_size}") # Original print
            else:
                 print("Warning: Cannot save size, locked item has no name.")
        # else: No need to save size if not locked

    def handle_window_drag_finished(self) -> None:
        """Saves configuration when window dragging finishes."""
        # 1. Update window position explicitly before saving
        current_pos = self._main_view.get_current_position()
        if current_pos:
            self._window_position = current_pos

        # 2. Check if a drawer is locked and visible, update its size
        if self._locked and self._locked_item_data:
            current_size = self._main_view.get_drawer_content_size()
            drawer_name = self._locked_item_data.get("name")
            if drawer_name:
                # Find and update the size directly in _drawers_data
                # Avoid calling update_drawer_size to prevent double saving
                updated = False
                for drawer in self._drawers_data:
                    if drawer.get("name") == drawer_name:
                        drawer["size"] = current_size
                        updated = True
                        print(f"[handle_window_drag_finished] Drawer '{drawer_name}' size updated in memory to {current_size}") # DEBUG
                        # print(f"Drawer '{drawer_name}' size updated to {current_size} on window drag finish.") # Original print
                        break
                if not updated:
                     print(f"Warning: Could not find locked drawer '{drawer_name}' to update size on drag finish.")

        # 3. Save configuration (includes updated position and potentially updated size)
        self.save_configuration()
        print("Window drag finished, configuration saved.")


    def handle_settings_requested(self) -> None:
        """Handles the request to open the settings dialog."""
        self._main_view.show_settings_dialog()

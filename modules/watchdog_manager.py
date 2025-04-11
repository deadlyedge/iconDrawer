import os # Import os for path normalization
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from PySide6.QtCore import QTimer, QObject, Signal, Slot # Import Slot
import logging
from typing import Dict, Set # Import Dict and Set for typing

class DrawerWatchdogManager(QObject):
    # Signal emitted AFTER debouncing in the main Qt thread
    directoryChanged = Signal(str)
    # Internal signal emitted immediately from watchdog thread to request scheduling in main thread
    _scheduleRefreshRequested = Signal(str)

    def __init__(self, controller, main_window):
        super().__init__()
        self.controller = controller # Keep controller reference if needed elsewhere, though not used in current logic
        # self.main_window = main_window # main_window seems unused, can be removed if not needed elsewhere
        self.observer = Observer()
        self._lock = threading.Lock() # Lock for accessing shared pending_refreshes dict
        # Store monitored paths for checking which root dir changed
        self.monitored_paths: Set[str] = set()
        # Use a dictionary to track pending refreshes per path (managed in main thread)
        self._pending_refreshes: Dict[str, QTimer] = {}

        # Connect the internal signal to the main thread processing slot
        self._scheduleRefreshRequested.connect(self._processRefreshRequest)


    def start(self, paths: list[str]):
        """启动监控，paths为目录路径列表"""
        event_handler = self._create_event_handler()
        logging.info(f"Watchdog starting monitoring for paths: {paths}")
        # Clear previous state if restarting
        self.monitored_paths.clear()
        with self._lock: # Ensure thread safety when clearing
            for timer in self._pending_refreshes.values():
                timer.stop()
            self._pending_refreshes.clear()

        normalized_paths = set()
        for path in paths:
            try:
                # Normalize paths for reliable comparison later
                norm_path = os.path.normcase(os.path.normpath(path))
                if os.path.isdir(norm_path): # Check if it's actually a directory
                    self.observer.schedule(event_handler, norm_path, recursive=True)
                    normalized_paths.add(norm_path)
                    logging.info(f"Watchdog scheduled monitoring for directory: {norm_path}")
                else:
                     logging.warning(f"Skipping watchdog for non-directory path: {path} (Normalized: {norm_path})")
            except Exception as e:
                logging.error(f"Failed to schedule monitoring for path: {path}, Error: {e}")

        self.monitored_paths = normalized_paths
        if self.monitored_paths:
            try:
                # Check if observer is already running before starting
                if not self.observer.is_alive():
                    self.observer.start()
                    logging.info("Watchdog observer started.")
                else:
                    logging.info("Watchdog observer already running.")
            except Exception as e:
                 logging.error(f"Failed to start watchdog observer: {e}")
        else:
            logging.warning("No valid directories provided to monitor.")

    def stop(self):
        """停止监控"""
        if self.observer.is_alive():
            try:
                self.observer.stop()
                self.observer.join() # Wait for the observer thread to finish
                logging.info("Watchdog observer stopped.")
            except Exception as e:
                logging.error(f"Error stopping watchdog observer: {e}")
        else:
            logging.info("Watchdog observer was not running.")
        # Clear state on stop
        self.monitored_paths.clear()
        with self._lock: # Ensure thread safety when clearing
            for timer in self._pending_refreshes.values():
                timer.stop()
            self._pending_refreshes.clear()


    def _create_event_handler(self):
        """Creates the filesystem event handler."""
        manager = self # Capture self for use inside the handler class

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent):
                # Ignore directory creation/deletion events themselves for simplicity,
                # focus on changes *within* monitored directories.
                if event.is_directory:
                    # logging.debug(f"Watchdog ignoring directory event: {event.event_type} - {event.src_path}")
                    return

                # Decode src_path to ensure it's a string
                # This runs in the watchdog thread
                try:
                    src_path_str = os.fsdecode(event.src_path)
                    logging.debug(f"Watchdog captured event: {event.event_type} - {src_path_str}")
                    manager._handle_event(src_path_str)
                except Exception as e:
                    logging.error(f"Error decoding/handling watchdog event path {event.src_path}: {e}")


        return Handler()

    def _handle_event(self, event_path: str):
        """Determines the root monitored path and requests a refresh schedule (runs in watchdog thread)."""
        # This method runs in the Watchdog thread
        try:
            normalized_event_path = os.path.normcase(os.path.normpath(event_path))
            affected_root_path = None

            # Find which monitored root path contains the event path
            # Access self.monitored_paths directly as it's usually set before observer starts
            # If paths could change dynamically while running, a lock might be needed here too
            for root_path in self.monitored_paths:
                if normalized_event_path.startswith(root_path + os.sep) or normalized_event_path == root_path:
                    # Ignore changes to the root directory itself? (Optional)
                    # if normalized_event_path == root_path and os.path.isdir(root_path):
                    #     continue
                    affected_root_path = root_path
                    break # Found the relevant root path

            if affected_root_path:
                logging.debug(f"Event path '{normalized_event_path}' belongs to monitored root '{affected_root_path}'. Requesting refresh schedule.")
                # Emit signal to request scheduling in the main thread instead of managing QTimer here
                self._scheduleRefreshRequested.emit(affected_root_path)
            else:
                logging.debug(f"Event path '{normalized_event_path}' not within any monitored root directory. Ignoring.")

        except Exception as e:
            logging.error(f"Error handling watchdog event for path {event_path}: {e}")

    @Slot(str)
    def _processRefreshRequest(self, root_path: str):
        """Handles the refresh request in the main Qt thread, managing debouncing."""
        # This slot runs in the main Qt thread because it's connected to _scheduleRefreshRequested signal
        with self._lock: # Protect access to shared _pending_refreshes
            # If a timer for this path already exists, just restart it (debouncing)
            if root_path in self._pending_refreshes:
                logging.debug(f"Debouncing refresh for {root_path}. Restarting timer.")
                self._pending_refreshes[root_path].start(500) # Restart timer with 500ms delay
                return

            # Otherwise, create a new timer
            logging.info(f"Scheduling delayed refresh signal for: {root_path}")
            timer = QTimer(self) # Parent timer to self (QObject) for proper cleanup
            timer.setSingleShot(True)
            # Use lambda to capture the current root_path for the timeout signal
            # Connect timeout to _emit_refresh_signal which will run in main thread
            timer.timeout.connect(lambda p=root_path: self._emit_refresh_signal(p))
            self._pending_refreshes[root_path] = timer
            timer.start(500) # Start timer with 500ms delay

    def _emit_refresh_signal(self, root_path: str):
        """Emits the directoryChanged signal (runs in main thread)."""
        # This method runs in the main Qt thread because it's called by QTimer timeout
        with self._lock: # Protect access to shared _pending_refreshes
            # Remove the timer now that it has fired
            if root_path in self._pending_refreshes:
                # Optional: stop timer explicitly before deleting? Usually not needed for single-shot.
                # self._pending_refreshes[root_path].stop()
                del self._pending_refreshes[root_path]
            else:
                # Should not happen if logic is correct, but log if it does
                logging.warning(f"Timer finished for path '{root_path}', but it was not found in pending refreshes.")
                # Still attempt to emit the signal? Or just return? Let's emit.
                # return

        logging.info(f"Emitting directoryChanged signal for path: {root_path}")
        self.directoryChanged.emit(root_path)

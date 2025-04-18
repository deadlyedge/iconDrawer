import os
import time
import threading
import logging
from typing import Dict, Set, List, Optional, NamedTuple
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# --- 文件信息结构 ---
class FileInfo(NamedTuple):
    name: str
    path: str
    is_dir: bool

# --- 目录监控相关结构 ---
class DrawerWatchdogManager(QObject):
    directoryChanged = Signal(str)
    _scheduleRefreshRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self.observer = Observer()
        self._lock = threading.Lock()
        self.monitored_paths: Set[str] = set()
        self._pending_refreshes: Dict[str, QTimer] = {}
        self._scheduleRefreshRequested.connect(self._processRefreshRequest)

    def start(self, paths: List[str]):
        event_handler = self._create_event_handler()
        logging.info(f"Watchdog starting monitoring for paths: {paths}")
        self.monitored_paths.clear()
        with self._lock:
            for timer in self._pending_refreshes.values():
                timer.stop()
            self._pending_refreshes.clear()

        normalized_paths = set()
        for path in paths:
            try:
                norm_path = os.path.normcase(os.path.normpath(path))
                if os.path.isdir(norm_path):
                    self.observer.schedule(event_handler, norm_path, recursive=True)
                    normalized_paths.add(norm_path)
                    logging.info(
                        f"Watchdog scheduled monitoring for directory: {norm_path}"
                    )
                else:
                    logging.warning(
                        f"Skipping watchdog for non-directory path: {path} (Normalized: {norm_path})"
                    )
            except Exception as e:
                logging.error(
                    f"Failed to schedule monitoring for path: {path}, Error: {e}"
                )

        self.monitored_paths = normalized_paths
        if self.monitored_paths:
            try:
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
        if self.observer.is_alive():
            try:
                self.observer.stop()
                self.observer.join()
                logging.info("Watchdog observer stopped.")
            except Exception as e:
                logging.error(f"Error stopping watchdog observer: {e}")
        else:
            logging.info("Watchdog observer was not running.")
        self.monitored_paths.clear()
        with self._lock:
            for timer in self._pending_refreshes.values():
                timer.stop()
            self._pending_refreshes.clear()

    def _create_event_handler(self):
        manager = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent):
                if event.is_directory:
                    return
                try:
                    src_path_str = os.fsdecode(event.src_path)
                    logging.debug(
                        f"Watchdog captured event: {event.event_type} - {src_path_str}"
                    )
                    manager._handle_event(src_path_str)
                except Exception as e:
                    logging.error(
                        f"Error decoding/handling watchdog event path {event.src_path}: {e}"
                    )

        return Handler()

    def _handle_event(self, event_path: str):
        try:
            normalized_event_path = os.path.normcase(os.path.normpath(event_path))
            affected_root_path = None
            for root_path in self.monitored_paths:
                if (
                    normalized_event_path.startswith(root_path + os.sep)
                    or normalized_event_path == root_path
                ):
                    affected_root_path = root_path
                    break
            if affected_root_path:
                logging.debug(
                    f"Event path '{normalized_event_path}' belongs to monitored root '{affected_root_path}'. Requesting refresh schedule."
                )
                self._scheduleRefreshRequested.emit(affected_root_path)
            else:
                logging.debug(
                    f"Event path '{normalized_event_path}' not within any monitored root directory. Ignoring."
                )
        except Exception as e:
            logging.error(f"Error handling watchdog event for path {event_path}: {e}")

    @Slot(str)
    def _processRefreshRequest(self, root_path: str):
        with self._lock:
            if root_path in self._pending_refreshes:
                logging.debug(f"Debouncing refresh for {root_path}. Restarting timer.")
                self._pending_refreshes[root_path].start(200)
                return
            logging.info(f"Scheduling delayed refresh signal for: {root_path}")
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda p=root_path: self._emit_refresh_signal(p))
            self._pending_refreshes[root_path] = timer
            timer.start(200)

    def _emit_refresh_signal(self, root_path: str):
        with self._lock:
            if root_path in self._pending_refreshes:
                del self._pending_refreshes[root_path]
            else:
                logging.warning(
                    f"Timer finished for path '{root_path}', but it was not found in pending refreshes."
                )
        logging.info(f"Emitting directoryChanged signal for path: {root_path}")
        self.directoryChanged.emit(root_path)

# --- DataManager 主体 ---
class DataManager(QObject):
    directoryChanged = Signal(str)  # 目录变动信号

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._file_cache: Dict[str, List[FileInfo]] = {}
        self._watchdog = DrawerWatchdogManager()
        self._watchdog.directoryChanged.connect(self._on_directory_changed)

    def start_monitor(self, paths: List[str]):
        self._watchdog.start(paths)

    def stop_monitor(self):
        self._watchdog.stop()

    def get_file_list(self, drawer_path: str) -> Optional[List[FileInfo]]:
        return self._file_cache.get(drawer_path)

    @Slot(str)
    def _on_directory_changed(self, path: str):
        # 目录变动时同步刷新缓存，并发出信号
        self.reload_drawer_content(path)
        self.directoryChanged.emit(path)

    def reload_drawer_content(self, drawer_path: str) -> List[FileInfo]:
        # 同步扫描目录，更新缓存
        file_list = []
        try:
            p = Path(drawer_path)
            if not p.is_dir():
                logging.warning(f"路径无效，无法刷新: {drawer_path}")
                self._file_cache[drawer_path] = []
                return []
            max_attempts = 5
            for attempt in range(max_attempts):
                file_list = []
                try:
                    time.sleep(0.2)
                    for child in p.iterdir():
                        file_list.append(
                            FileInfo(
                                name=child.name, path=str(child), is_dir=child.is_dir()
                            )
                        )
                except Exception as e:
                    logging.warning(f"扫描目录异常: {e}")
                    file_list = []
                if file_list:
                    break
            self._file_cache[drawer_path] = file_list
            logging.debug(f"同步刷新抽屉内容完成: {drawer_path}, 共{len(file_list)}项")
            return file_list
        except Exception as e:
            logging.error(f"同步刷新抽屉内容失败: {drawer_path}, 错误: {e}")
            self._file_cache[drawer_path] = []
            return []

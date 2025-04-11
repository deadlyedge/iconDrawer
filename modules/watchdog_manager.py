import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from PySide6.QtCore import QTimer, QObject, Signal
import logging

class DrawerWatchdogManager(QObject):
    directoryChanged = Signal(str)

    def __init__(self, controller, main_window):
        super().__init__()
        self.controller = controller
        self.main_window = main_window
        self.observer = Observer()
        self._lock = threading.Lock()
        self._pending_refresh = False
        self._refresh_timer = None

    def start(self, paths):
        """启动监控，paths为目录路径列表"""
        event_handler = self._create_event_handler()
        logging.info(f"准备监控目录列表: {paths}")
        for path in paths:
            try:
                self.observer.schedule(event_handler, path, recursive=True)
                logging.info(f"Watchdog已开始监控目录: {path}")
            except Exception as e:
                logging.error(f"监控目录失败: {path}, 错误: {e}")
        self.observer.start()

    def stop(self):
        """停止监控"""
        self.observer.stop()
        self.observer.join()

    def _create_event_handler(self):
        manager = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent):
                # 任何文件变化都触发
                logging.info(f"Watchdog捕获事件: {event.event_type} - {event.src_path}")
                manager._on_directory_changed(event)

        return Handler()

    def _on_directory_changed(self, event):
        # 只刷新当前显示的抽屉
        current_drawer = self.controller._locked_item_data
        if not current_drawer:
            logging.debug("当前无锁定抽屉，忽略事件")
            return
        current_path = current_drawer.get("path")
        if not current_path:
            logging.debug("当前抽屉无路径，忽略事件")
            return

        # 判断变化是否在当前抽屉目录下
        if not event.src_path.startswith(current_path):
            logging.debug(f"事件路径 {event.src_path} 不在当前抽屉目录 {current_path} 下，忽略")
            return

        with self._lock:
            if self._pending_refresh:
                logging.debug("已有刷新计划，忽略本次事件")
                return
            self._pending_refresh = True

        logging.info(f"检测到变化，计划延迟刷新抽屉: {current_path}")

        # 延迟500ms后发射信号，通知controller刷新
        def emit_signal():
            with self._lock:
                self._pending_refresh = False
            self.directoryChanged.emit(current_path)

        QTimer.singleShot(500, emit_signal)

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon # Import QIcon
from PySide6.QtCore import QFile, QIODevice, QTextStream
import logging
from modules.main_window import MainWindow
from modules.watchdog_manager import DrawerWatchdogManager  # 导入watchdog管理器

# Configure basic logging (adjust level and format as needed for production)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
    logging.info("Application starting...")

    app = QApplication(sys.argv)

    # Set Application Icon (same as tray icon)
    app_icon = QIcon("asset/drawer.icon.4.ico")
    if app_icon.isNull():
        logging.warning("Application icon file 'asset/drawer.icon.4.ico' not found or invalid.")
    app.setWindowIcon(app_icon)

    # Load and apply the stylesheet using QTextStream
    style_file = QFile("modules/style.qss")
    if style_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
        stream = QTextStream(style_file)
        stylesheet = stream.readAll()
        app.setStyleSheet(stylesheet)
        style_file.close()
        logging.info("Stylesheet 'modules/style.qss' loaded successfully.")
    else:
        logging.error(f"Could not open stylesheet file 'modules/style.qss': {style_file.errorString()}")

    mainWindow = MainWindow()
    # mainWindow.resize(800, 600) # Initial resize might not be needed if hidden - handled by settings?
    mainWindow.show() # Don't show initially, rely on tray icon to show/hide

    # 初始化watchdog
    watchdog_manager = DrawerWatchdogManager(mainWindow.controller, mainWindow)
    # 连接watchdog信号到controller槽
    if mainWindow.controller is not None:
        watchdog_manager.directoryChanged.connect(mainWindow.controller.on_directory_changed)
    else:
        logging.error("Controller 未初始化，无法连接 watchdog 信号")

    # 获取所有抽屉目录路径
    drawer_paths = []
    try:
        if mainWindow.controller:
            drawers_data = mainWindow.controller._drawers_data
            drawer_paths = [d.get("path") for d in drawers_data if d.get("path")]
        else:
            logging.error("MainWindow.controller 未初始化，无法获取抽屉目录")
    except Exception as e:
        logging.error(f"获取抽屉目录失败: {e}")

    watchdog_manager.start(drawer_paths)

    try:
        exit_code = app.exec()
    finally:
        # 程序退出时停止watchdog
        watchdog_manager.stop()

    sys.exit(exit_code)

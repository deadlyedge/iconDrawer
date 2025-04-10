import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon # Import QIcon
from PySide6.QtCore import QFile, QIODevice, QTextStream
import logging
from modules.main_window import MainWindow

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
    
    sys.exit(app.exec())

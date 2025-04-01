import sys
from PySide6.QtWidgets import QApplication
from modules.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.resize(800, 600)
    mainWindow.show()
    sys.exit(app.exec())

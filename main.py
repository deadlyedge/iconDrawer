import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice, QTextStream
from modules.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load and apply the stylesheet using QTextStream
    style_file = QFile("modules/style.qss")
    if style_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
        stream = QTextStream(style_file)
        stylesheet = stream.readAll()
        app.setStyleSheet(stylesheet)
        style_file.close()
    else:
        print(f"Could not open stylesheet file: {style_file.errorString()}")

    mainWindow = MainWindow()
    mainWindow.resize(800, 600)
    mainWindow.show()
    sys.exit(app.exec())

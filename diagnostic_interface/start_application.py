import sys
import os
sys.path.insert(0, os.getcwd())
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import qdarktheme


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # PyQt Theme
    app.setStyleSheet(qdarktheme.load_stylesheet("light"))

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec_())

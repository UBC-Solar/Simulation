import sys
import os
sys.path.insert(0, os.getcwd())

from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
#from qt_material import apply_stylesheet


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # PyQt Theme
   # apply_stylesheet(app, theme='light_blue.xml', invert_secondary=True)

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec_())

import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import qdarktheme
from qt_material import apply_stylesheet


if __name__ == "__main__":
    app = QApplication(sys.argv)

    #!!!
    app.setStyleSheet(qdarktheme.load_stylesheet("light"))
    #apply_stylesheet(app, theme = "dark_teal.xml")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

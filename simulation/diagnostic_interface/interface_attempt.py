import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np


class PlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt with Interactive Matplotlib")

        # Data
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x)

        # Matplotlib figure
        self.figure, self.ax = plt.subplots()
        self.ax.plot(x, y)
        self.ax.set_title("Interactive Matplotlib Plot in PyQt")

        # Canvas widget
        self.canvas = FigureCanvas(self.figure)

        # Navigation toolbar for interactivity
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)  # Add the toolbar first for better UI
        layout.addWidget(self.canvas)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlotWindow()
    window.show()
    sys.exit(app.exec_())
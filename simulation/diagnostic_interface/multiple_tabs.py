import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class PlotTab(QWidget):
    def __init__(self, plot_function, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # Create Matplotlib figure and canvas
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)

        # Call the provided function to draw the plot
        plot_function(self.ax)

        # Add canvas to layout
        self.layout.addWidget(self.canvas)


def plot_sine(ax):
    x = np.linspace(0, 10, 100)
    ax.plot(x, np.sin(x), label="Sine Wave")
    ax.legend()


def plot_cosine(ax):
    x = np.linspace(0, 10, 100)
    ax.plot(x, np.cos(x), label="Cosine Wave", color="red")
    ax.legend()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multiple Plots in Tabs")

        layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        # Create tabs with different plots
        tab1 = PlotTab(plot_sine)
        tab2 = PlotTab(plot_cosine)

        # Add tabs to QTabWidget
        tab_widget.addTab(tab1, "Sine Wave")
        tab_widget.addTab(tab2, "Cosine Wave")

        layout.addWidget(tab_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())

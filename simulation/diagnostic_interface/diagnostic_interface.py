import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np
from data_tools import SunbeamClient


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)  # Ensure it's integrated into the UI
        self.query_and_plot("FSGP", 3, "VehicleVelocity")

    def queryData(self, race: str, day: int, data_name: str):
        """Queries the Sunbeam database for the requested data."""
        client = SunbeamClient()
        file = client.get_file("influxdb_cache", f"{race}_2024_Day_{day}", "ingress", f"{data_name}")
        print("Querying data...")
        result = file.unwrap()

        # Attempt to extract data properly
        if hasattr(result, 'values'):
            return result.values  # Preferred access
        elif hasattr(result, 'data'):
            return result.data  # Alternative access
        else:
            raise ValueError("Unable to extract data from the queried file.")

    def query_and_plot(self, race: str, day: int, data_name: str):
        """Fetches data and updates the plot."""
        try:
            data = self.queryData(race, day, data_name)
            self.ax.clear()  # Clear previous plots
            self.ax.plot(data)
            self.ax.set_title(f"{data_name} in {race} Day {day}")
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel(f"{data_name} (units)")
            self.draw()  # Refresh the canvas
        except Exception as e:
            print(f"Error fetching or plotting data: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Data Visualization")

        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        self.canvas = PlotCanvas(self)  # Add the plot canvas
        self.toolbar = NavigationToolbar(self.canvas, self)  # Add interactivity toolbar

        # Add widgets
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        central_widget.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

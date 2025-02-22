import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QLabel, QComboBox, QLineEdit, QFormLayout, QVBoxLayout, QTabWidget, QToolTip
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from data_tools import SunbeamClient


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

    def queryData(self, race: str, day: int, data_name: str):
        client = SunbeamClient()
        file = client.get_file("influxdb_cache", f"{race}_2024_Day_{day}", "ingress", f"{data_name}")
        print("Querying data...")
        result = file.unwrap()

        if hasattr(result, 'values'):
            return result.values
        elif hasattr(result, 'data'):
            return result.data
        else:
            raise ValueError("Unable to extract data from the queried file.")

    def query_and_plot(self, race: str, day: int, data_name: str):
        try:
            data = self.queryData(race, day, data_name)
            self.ax.clear()
            self.ax.plot(data)
            self.ax.set_title(f"{data_name} in {race} Day {day}")
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel(f"{data_name} (units)")
            self.draw()
        except Exception as e:
            print(f"Error fetching or plotting data: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diagnostic Interface")
        self.setGeometry(100, 100, 800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_home_tab()

    def create_home_tab(self):
        home_widget = QWidget()
        layout = QVBoxLayout()
        client = SunbeamClient()

        title_label = QLabel("Select Data to Plot")
        title_label.setFont(QFont("Arial", 20))
        title_label.move(0, 222)
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        self.race_input = QComboBox()
        events = client.distinct("event", {"origin" : "influxdb_cache"})
        self.race_input.addItems(events)

        self.day_input = QLineEdit()
        self.day_input.setPlaceholderText("Enter day (e.g., 3)")

        self.data_input = QComboBox()
        names = client.distinct( "name", {"origin" : "influxdb_cache"})
        self.data_input.addItems(names)

        form_layout.addRow("Event:", self.race_input)
        form_layout.addRow("Day:", self.day_input)
        form_layout.addRow("Data:", self.data_input)
        layout.addLayout(form_layout)

        QToolTip.setFont(QFont('Arial', 14)) # Testing ToolTip


        self.submit_button = QPushButton("Load Data")
        self.submit_button.clicked.connect(self.create_plot_tab)
        self.submit_button.setToolTip("TESTING TOOLTIP") # Adding tooltip for button
        layout.addWidget(self.submit_button)

        home_widget.setLayout(layout)
        self.tabs.addTab(home_widget, "Home")

    def create_plot_tab(self):
        race = self.race_input.currentText()
        day = self.day_input.text()
        data_name = self.data_input.currentText()

        if not day.isdigit():
            print("Invalid day input")
            return

        plot_widget = QWidget()
        layout = QVBoxLayout()
        canvas = PlotCanvas()
        toolbar = NavigationToolbar(canvas, self)

        layout.addWidget(toolbar)
        layout.addWidget(canvas)

        close_button = QPushButton("Close Tab")
        close_button.clicked.connect(lambda: self.close_tab(plot_widget))
        layout.addWidget(close_button)

        plot_widget.setLayout(layout)
        self.tabs.addTab(plot_widget, f"{data_name} - {race} Day {day}")
        self.tabs.setCurrentWidget(plot_widget)

        canvas.query_and_plot(race, int(day), data_name)

    def close_tab(self, widget):
        index = self.tabs.indexOf(widget)
        if index != -1:
            self.tabs.removeTab(index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

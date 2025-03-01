import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QLabel, QComboBox, QLineEdit, QFormLayout, QVBoxLayout,
    QTabWidget, QToolTip, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from data_tools import SunbeamClient

# Dictionary to store help messages for each plot
HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time (s)\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}


class CustomNavigationToolbar(NavigationToolbar):
    """Custom toolbar with tooltips for each button."""

    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)

        # Define tooltips for each standard tool in the toolbar
        tooltips = {
            "Home": "Reset view.",
            "Back": "Go back to the previous view.",
            "Forward": "Move forward in the view history.",
            "Pan": "Click and drag to move the plot.",
            "Zoom": "Select a region to zoom in.",
            "Save": "Save the current plot as an image file."
        }

        # Loop through toolbar buttons and set tooltips
        for action in self.actions():
            text = action.text()
            if text in tooltips:
                action.setToolTip(tooltips[text])


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

    def queryData(self, event: str, data_name: str):
        """
        This method queries data from SunBeam as a file, and later unwraps it.

        param String event: Race type and race day.
        param String data_name: The type of data that is being queried (eg. Vehicle_Velocity)
        return: Returns a TimeSeries with the values you wanted to query.
        """
        client = SunbeamClient()
        file = client.get_file("influxdb_cache", f"{event}", "ingress", f"{data_name}")
        print("Querying data...")
        result = file.unwrap()

        if hasattr(result, 'values'):
            return result.values
        elif hasattr(result, 'data'):
            return result.data
        else:
            raise ValueError("Unable to extract data from the queried file.")

    def query_and_plot(self, event: str, data_name: str):
        """
        This method calls on queryData and then plots the data returned.

        param String event: Race type and race day.
        param String data_name: The type of data that is being queried (eg. Vehicle_Velocity)
        """
        try:
            data = self.queryData(event, data_name)
            self.ax.clear()
            self.ax.plot(data)
            self.ax.set_title(f"{data_name} in {event}")
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

        # Aesthetic changes
        home_widget.setStyleSheet("background-color: #4bb4de;")

        # Load and add the team logo
        logo_label = QLabel()
        logo_label.setPixmap(QPixmap("Solar_Logo.png").scaled(800, 600, Qt.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignCenter)  # Center the image
        layout.addWidget(logo_label)

        # Title Label
        title_label = QLabel("Select Data to Plot")
        title_label.setFont(QFont("Arial", 20))
        layout.addWidget(title_label)

        # Setting up events
        form_layout = QFormLayout()
        self.event_input = QComboBox()
        events = client.distinct("event", {"origin": "influxdb_cache"})  # Checks all the events available in Sunbeam
        self.event_input.addItems(events)
        self.event_input.setStyleSheet("background-color: white")

        # Setting up data types that can be queried
        self.data_input = QComboBox()
        names = client.distinct("name", {"origin": "influxdb_cache"})  # Checks all the data types available in Sunbeam
        self.data_input.addItems(names)
        self.data_input.setStyleSheet("background-color: white")

        form_layout.addRow("Event:", self.event_input)
        form_layout.addRow("Data:", self.data_input)
        layout.addLayout(form_layout)

        # Button to load the plot
        self.submit_button = QPushButton("Load Data")
        self.submit_button.clicked.connect(self.create_plot_tab)
        self.submit_button.setStyleSheet("background-color: white")
        layout.addWidget(self.submit_button)

        home_widget.setLayout(layout)
        self.tabs.addTab(home_widget, "Home")

    def create_plot_tab(self):
        event = self.event_input.currentText()
        data_name = self.data_input.currentText()

        plot_widget = QWidget()
        layout = QVBoxLayout()
        canvas = PlotCanvas()

        #toolbar = NavigationToolbar(canvas, self)
        toolbar = CustomNavigationToolbar(canvas, self)

        layout.addWidget(toolbar)
        layout.addWidget(canvas)

        # Help Button that displays more information on the graph
        help_button = QPushButton("Help")
        help_button.clicked.connect(lambda: self.show_help_message(data_name, event))
        layout.addWidget(help_button)

        # Button that closes the tab with the plot
        close_button = QPushButton("Close Tab")
        close_button.clicked.connect(lambda: self.close_tab(plot_widget))
        layout.addWidget(close_button)

        plot_widget.setLayout(layout)
        self.tabs.addTab(plot_widget, f"{data_name} - {event}")
        self.tabs.setCurrentWidget(plot_widget)

        canvas.query_and_plot(event, data_name)

    def close_tab(self, widget):
        index = self.tabs.indexOf(widget)
        if index != -1:
            self.tabs.removeTab(index)

    def show_help_message(self, data_name, event):
        """
        After you have clicked on the help button, this function displays a help message with more information on the plot
        """
        message = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")

        QMessageBox.information(self, f"Help: {data_name}", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

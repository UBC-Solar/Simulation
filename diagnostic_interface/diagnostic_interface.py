import sys

import numpy as np
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QLabel, QComboBox, QLineEdit, QFormLayout, QVBoxLayout,
    QTabWidget, QToolTip, QMessageBox, QAction, QFileDialog
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from data_tools import SunbeamClient, TimeSeries
import pandas as pd
import matplotlib


"""Check that references to tabs are deleted after tab is closed because I don't want to occupy too much memory."""
# Dictionary to store help messages for each plot
HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time (s)\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

# Interface aesthetic parameters
WINDOW_TITLE = "Diagnostic Interface"
X_COORD = 100 # Sets the x-coord where the interface will be created
Y_COORD = 100 # Sets the y-coord where the interface will be created
WIDTH = 800 # Sizing of window
HEIGHT = 600 # Size of window


class CustomNavigationToolbar(NavigationToolbar):
    """Custom toolbar with tooltips for each button."""

    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)

        # Load a save icon (matching Matplotlib's style)
        save_icon = QIcon(matplotlib.get_data_path() + "/images/filesave.png")

        # Add a "Save Data" button to the toolbar for saving data as a csv
        self.save_data_action = self.addAction(save_icon, "Save Data")
        self.save_data_action.setToolTip("Save the plotted data as a CSV file.")
        self.save_data_action.triggered.connect(self.canvas.save_data_to_csv)
        self.addAction(self.save_data_action)

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
        self.current_data = None  # Store data for saving
        self.current_data_name = ""
        self.current_event = ""
        self.current_origin = ""
        self.current_source = ""

    def query_data(self, origin: str, source: str, event: str, data_name: str) -> TimeSeries:
        """
        This method queries data from SunBeam as a file, and later unwraps it.

        :param str origin: pipeline name
        :param str source: pipeline stage
        :param str event: race type and race day.
        :param str data_name: the type of data that is being queried (e.g. Vehicle_Velocity).
        :raises ValueError: if it is not possible to extract data from the queried file.
        :returns: a TimeSeries with the values you wanted to query.
        """
        client = SunbeamClient()
        file = client.get_file(origin, event, source, data_name)
        result = file.unwrap()

        if hasattr(result, 'values'):
            return result.values
        elif hasattr(result, 'data'):
            return result.data
        else:
            raise ValueError("Unable to extract data from the queried file.")

    def query_and_plot(self, origin: str, source: str, event: str, data_name: str) -> bool:
        """
        This method calls on query_data and then plots the data returned.

        :param str origin: pipeline name
        :param str source: pipeline stage
        :param str event: race type and race day.
        :param str data_name: the type of data that is being queried (e.g. Vehicle_Velocity).
        :raises TypeError: if the data is not a TimeSeries
        :returns bool: depending on whether it was possible to query and plot the data
        """
        try:
            data = self.query_data(origin, source, event, data_name) # Get the data from Sunbeam

            # Checking data is a TimeSeries
            if not isinstance(data, TimeSeries):
                raise TypeError("Expected TimeSeries, but got a different type of data.")

            self.current_data = data  # Store data for saving
            self.current_data_name = data_name
            self.current_event = event
            self.current_origin = origin
            self.current_source = source
            self.ax.clear()
            self.ax.plot(data.datetime_x_axis,data)
            self.ax.set_title(f"{data_name} - {event} - {origin} - {source}")
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel(f"{data_name} ({data.units})")
            self.draw()
            return True
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Plotting Error")
            msg.setText("Error fetching or plotting data.")
            msg.setInformativeText(str(e))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return False  # Indicate failure so the tab can be closed in a later method

    def save_data_to_csv(self):
        """
        Saves the current data as a CSV file.
        """
        if self.current_data is None:
            print("No data available to save.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            None, "Save Data", f"{self.current_data_name}_{self.current_event}_{self.current_origin}_{self.current_source}.csv",
            "CSV Files (*.csv);;All Files (*)", options=options
        )

        if file_name:
            df = pd.DataFrame({'Time (s)': range(len(self.current_data)), f"{self.current_data_name}": self.current_data})
            df.to_csv(file_name, index=False)
            print(f"Data saved to {file_name}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(X_COORD, Y_COORD, WIDTH, HEIGHT)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.create_home_tab()

        # Create a timer to refresh plots
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_all_tabs)
        self.refresh_timer.start(120000) # 2 minutes refresh time

    def refresh_all_tabs(self):
        """
        Refreshes all open plot tabs by requerying data and replotting it.
        """
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)  # This is a QWidget (plot_widget)
            plot_canvas = widget.findChild(PlotCanvas)  # Find PlotCanvas inside

            if plot_canvas:  # Ensure there's a plot inside
                plot_canvas.query_and_plot(plot_canvas.current_origin, plot_canvas.current_source,
                                           plot_canvas.current_event, plot_canvas.current_data_name)


    def create_home_tab(self) -> None:
        """
        Creates home tab for the diagnostic interface. The home tab
        contains dropdown menus so that we can choose what data we
        want to query and plot.
        """
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
        form_layout = QFormLayout()

        # Dropdown menus
        self.origin_input = QComboBox()
        self.event_input = QComboBox()
        self.source_input = QComboBox()
        self.data_input = QComboBox()

        # Load initial data
        self.origins = client.distinct("origin", [])
        self.origin_input.addItems(self.origins)

        self.events = client.distinct("event", [])
        self.event_input.addItems(self.events)

        self.sources = client.distinct("source", [])
        self.source_input.addItems(self.sources)

        self.data_types = client.distinct("name", [])
        self.data_input.addItems(self.data_types)

        # Style of the drowpdown menus
        for combo in [self.origin_input, self.source_input, self.event_input, self.data_input]:
            combo.setStyleSheet("background-color: white")

        # Add to form layout
        form_layout.addRow("Origin:", self.origin_input)
        form_layout.addRow("Event:", self.event_input)
        form_layout.addRow("Source:", self.source_input)
        form_layout.addRow("Data:", self.data_input)

        layout.addLayout(form_layout)

        # Button to load the plot
        submit_button = QPushButton("Load Data")
        submit_button.clicked.connect(self.create_plot_tab)
        submit_button.setStyleSheet("background-color: white")
        layout.addWidget(submit_button)

        home_widget.setLayout(layout)
        self.tabs.addTab(home_widget, "Home")

        # Callbacks to update dropdowns to only show existing query combinations
        self.origin_input.currentTextChanged.connect(self.update_filters)
        self.event_input.currentTextChanged.connect(self.update_filters)
        self.source_input.currentTextChanged.connect(self.update_filters)

    def update_filters(self) -> None:
        """
        Updates all dropdown options based on selected values. This way, you should only
        be able to form query combinations that make sense. For example, if you choose
        'realtime' as your origin, in the events dropdown you should only see 'FSGP_2024_Day_1'
        because that is the only event associated to the 'realtime' pipeline.

        :raises Exception: if there is an error while updating the dropdown options.
        """
        try:
            client = SunbeamClient()

            # Initial text
            selected_origin = self.origin_input.currentText()
            selected_source = self.source_input.currentText()
            selected_event = self.event_input.currentText()
            selected_data = self.data_input.currentText()

            # Get valid events based on origin
            available_events = set(client.distinct("event", []))  # Start with all events
            if selected_origin:
                available_events &= set(client.distinct("event", {"origin": selected_origin})) # Filter by origin

            # Get valid sources based on origin and event
            available_sources = set(client.distinct("source", []))  # Start with all
            if selected_origin:
                available_sources &= set(client.distinct("source", {"origin": selected_origin})) # Filter by origin
            if selected_event:
                available_sources &= set(client.distinct("source", {"event": selected_event})) # Filter by event

            # Get valid data types based on origin, source, and event
            available_data = set(client.distinct("name", [])) # Start with all data
            if selected_origin:
                available_data &= set(client.distinct("name", {"origin": selected_origin})) # Filter by origin
            if selected_event:
                available_data &= set(client.distinct("name", {"event": selected_event})) # Filter by event
            if selected_source:
                available_data &= set(client.distinct("name", {"source": selected_source})) # Filter by source

            # Convert back to lists
            available_sources = list(available_sources)
            available_events = list(available_events)
            available_data = list(available_data)

            # Update dropdowns safely
            self.source_input.blockSignals(True) # Shuts down ability to take input
            self.source_input.clear()
            self.source_input.addItems(available_sources)
            # Set the selected source to the first available or keep it if it exists
            if selected_source in available_sources:
                self.source_input.setCurrentText(selected_source)
            elif available_sources:
                self.source_input.setCurrentText(available_sources[0])  # Select first available option
            self.source_input.blockSignals(False) # Can take inputs again

            self.event_input.blockSignals(True) # Can't take inputs
            self.event_input.clear()
            self.event_input.addItems(available_events)
            # Set the selected event to the first available or keep it if it exists
            if selected_event in available_events:
                self.event_input.setCurrentText(selected_event)
            elif available_events:
                self.event_input.setCurrentText(available_events[0])  # Select first available option
            self.event_input.blockSignals(False) # Can take inputs again

            self.data_input.blockSignals(True) # Can't take inputs
            self.data_input.clear()
            self.data_input.addItems(available_data)
            # Set the selected data to the first available or keep it if it exists
            if selected_data in available_data:
                self.data_input.setCurrentText(selected_data)
            elif available_data:
                self.data_input.setCurrentText(available_data[0])  # Select first available option
            self.data_input.blockSignals(False) # Can take inputs again

        except Exception as e:
            print(f"Error updating filters: {e}")

    def create_plot_tab(self) -> None:
        """
        Creates a new tab in the application. Once we have the tab, it creates a plot
        based on the options you chose in the dropdown menus. The tab includes a
        toolbar for interacting with plots, a help button, and a button to close it.
        """
        # Gets information from dropdown menus about which data we will plot.
        origin: str = self.origin_input.currentText()
        source: str = self.source_input.currentText()
        event: str = self.event_input.currentText()
        data_name: str = self.data_input.currentText()

        plot_widget = QWidget()
        layout = QVBoxLayout()
        canvas = PlotCanvas()

        toolbar = CustomNavigationToolbar(canvas, self) # Adding toolbar

        # Adding widgets to the tab
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
        self.tabs.addTab(plot_widget, f"{data_name} - {event} - {origin} - {source}")
        self.tabs.setCurrentWidget(plot_widget)

        # If there are any errors with querying and/or plotting data, close the tab.
        if not canvas.query_and_plot(origin, source, event, data_name):
            self.close_tab(plot_widget)

    def close_tab(self, widget) -> None:
        """
        Closes the current tab.

        :param QWidget widget: an element of the GUI you can interact with. In this case, it is the plot.
        """
        index: int = self.tabs.indexOf(widget) # Checks the index of the tab we want to close; if the tab is not in self.tabs, returns -1
        if index != -1: # Checks that the tab we want to close is in self.tabs. If it isn't (index == -1), do nothing
            self.tabs.removeTab(index) # If the tab is in self.tabs (index!= -1), we remove it

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
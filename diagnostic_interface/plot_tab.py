from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox
from plot_canvas import PlotCanvas
from custom_toolbar import CustomNavigationToolbar
from PyQt5.QtCore import pyqtSignal

# Dictionary to store help messages for each plot
HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time (s)\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

class PlotTab(QWidget):
    close_requested = pyqtSignal(QWidget)  # Signal to notify MainWindow to close this tab.

    def __init__(self, origin, source, event, data_name, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.plot_canvas = PlotCanvas(self)
        self.toolbar = CustomNavigationToolbar(canvas = self.plot_canvas)  # Creating toolbar
        self.layout.addWidget(self.toolbar) # Adding toolbar
        self.layout.addWidget(self.plot_canvas) # Adding space for plots
        self.setLayout(self.layout)

        # Help Button that displays more information on the graph
        help_button = QPushButton("Help")
        help_button.clicked.connect(lambda: self.show_help_message(data_name, event))
        self.layout.addWidget(help_button)

        # Button that closes the tab with the plot
        close_button = QPushButton("Close Tab")
        close_button.clicked.connect(self.request_close)
        self.layout.addWidget(close_button)

        # Query and plot the initial data
        self.plot_canvas.query_and_plot(origin, source, event, data_name)

    def refresh_plot(self):
        """Updates the data that exists in plot_canvas by rerunning query_and_plot
        and replacing the current instance with the new result."""
        self.plot_canvas.query_and_plot(
            self.plot_canvas.current_origin,
            self.plot_canvas.current_source,
            self.plot_canvas.current_event,
            self.plot_canvas.current_data_name
        )

    def request_close(self):
        """Emit signal to request closing this tab."""
        self.close_requested.emit(self)

    def show_help_message(self, data_name, event):
        """
        After you have clicked on the help button, this function displays a help message with more information on the plot.
        """
        message = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")

        QMessageBox.information(self, f"Help: {data_name}", message)

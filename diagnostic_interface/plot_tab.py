from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QGroupBox, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal
from diagnostic_interface import CustomNavigationToolbar, PlotCanvas

HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}


class PlotTab(QWidget):
    close_requested = pyqtSignal(QWidget)

    def __init__(self, origin: str, source: str, event: str, data_name: str, parent=None):
        super().__init__(parent)

        self.origin = origin
        self.source = source
        self.event = event
        self.data_name = data_name

        # Layout setup
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        self.plot_canvas = PlotCanvas(self)
        self.toolbar = CustomNavigationToolbar(canvas=self.plot_canvas)

        # Buttons
        help_button = QPushButton("Help")
        help_button.setObjectName("helpButton")
        help_button.clicked.connect(lambda: self.show_help_message(data_name, event))

        close_button = QPushButton("Close Tab")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.request_close)

        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout()
        button_layout.addWidget(help_button)
        button_layout.addWidget(close_button)
        button_group.setLayout(button_layout)

        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.plot_canvas)
        self.layout.addWidget(button_group)

        self.setStyleSheet("""
            QPushButton#helpButton, QPushButton#closeButton {
                padding: 6px 12px;
                border-radius: 8px;
            }
        """)

        if not self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name):
            self.request_close()

    def refresh_plot(self):
        if not self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name):
            self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name, event):
        message = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message)

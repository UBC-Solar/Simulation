from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QGroupBox, QHBoxLayout
)
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot

from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, PlotCanvas
from data_tools.collections import TimeSeries


HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

EVENT = "FSGP_2024_Day_1"


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object)  # emits the TimeSeries
    error = pyqtSignal(str)  # emits an error message


class PlotRefreshWorker(QRunnable):
    def __init__(self, plot_canvas: PlotCanvas, origin, source, event, data_name):
        super().__init__()
        self.plot_canvas = plot_canvas
        self.origin = origin
        self.source = source
        self.event = event
        self.data_name = data_name
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            data = self.plot_canvas.fetch_data(self.origin, self.event, self.source, self.data_name)
            self.signals.data_ready.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))


class PlotTab(QWidget):
    close_requested = pyqtSignal(QWidget)

    def __init__(self, origin: str, source: str, event: str, data_name: str, parent=None):
        super().__init__(parent)

        self.origin = origin
        self.source = source
        self.event = event
        self.data_name = data_name

        self._thread_pool = QThreadPool()

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

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plot)

        QTimer.singleShot(0, self.refresh_plot)

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.refresh_timer.setInterval(settings.plot_timer_interval * 1000)
            self.refresh_timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.refresh_timer.stop()

    def refresh_plot(self):
        worker = PlotRefreshWorker(
            self.plot_canvas,
            self.origin,
            self.source,
            self.event,
            self.data_name
        )
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self._thread_pool.start(worker)

    @pyqtSlot(object)
    def _on_data_ready(self, data: TimeSeries):
        self.plot_canvas.plot(data, f"{self.data_name}", data.units)

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)
        self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name, event):
        message = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message)

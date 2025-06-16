from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QGroupBox, QHBoxLayout
)
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
#from poetry.console.commands import self

from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, PlotCanvas2, IntegralPlot, RealtimeCanvas


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object, object)
    error = pyqtSignal(str)


HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

EVENT = "FSGP_2024_Day_1"


class PlotRefreshWorker(QRunnable):
    def __init__(self, plot_canvas: RealtimeCanvas, plot_canvas2: PlotCanvas2):
        super().__init__()
        self.plot_canvas: RealtimeCanvas = plot_canvas
        self.plot_canvas2: PlotCanvas2 = plot_canvas2
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            plot_canvas_1_data = self.plot_canvas.fetch_data()
            plot_canvas_2_data = self.plot_canvas2.fetch_data()
            self.signals.data_ready.emit(plot_canvas_1_data, plot_canvas_2_data)

        except Exception as e:
            self.signals.error.emit(str(e))


class WeatherTab(QWidget):
    close_requested = pyqtSignal(QWidget)

    def __init__(self, parent=None):

        super().__init__(parent)
        self._thread_pool = QThreadPool()

        # Layout setup
        #self.layout = QVBoxLayout(self)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(30, 30, 30, 30)

        plot1_layout = QVBoxLayout()

        self.plot_canvas1 = RealtimeCanvas("weather", "GHI")
        self.data_name = "GHI"

        self.toolbar1 = CustomNavigationToolbar(canvas=self.plot_canvas1)
        plot1_layout.addWidget(self.toolbar1)
        plot1_layout.addWidget(self.plot_canvas1)

        plot2_layout = QVBoxLayout()

        self.plot_canvas2 = PlotCanvas2()
        self.toolbar2 = CustomNavigationToolbar(canvas=self.plot_canvas2)

        plot2_layout.addWidget(self.toolbar2)
        plot2_layout.addWidget(self.plot_canvas2)

        plot3_layout = QVBoxLayout()

        self.plot_canvas3 = IntegralPlot(self)
        self.toolbar3 = CustomNavigationToolbar(canvas=self.plot_canvas3)
        plot3_layout.addWidget(self.toolbar3)
        plot3_layout.addWidget(self.plot_canvas3)

        bottom_plots_layout = QHBoxLayout()

        #bottom_plots_layout.addWidget(self.label)
        bottom_plots_layout.addLayout(plot2_layout)
        bottom_plots_layout.addLayout(plot3_layout)

        self.layout.addLayout(plot1_layout, stretch=6)
        self.layout.addLayout(bottom_plots_layout, stretch=4)

        help_button = QPushButton("Help")
        help_button.setObjectName("helpButton")
        help_button.clicked.connect(lambda: self.show_help_message(self.data_name))

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plot)

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.refresh_timer.setInterval(settings.plot_timer_interval * 1000)
            self.refresh_timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.refresh_timer.stop()

    def refresh_plot(self):

        worker = PlotRefreshWorker(self.plot_canvas1, self.plot_canvas2)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self._thread_pool.start(worker)

    @pyqtSlot(object, object)
    def _on_data_ready(self, plot1_data, plot_2_data):
        self.plot_canvas1.plot(plot1_data, "GHI", "Irradiance (W/m^2)")
        self.plot_canvas2.plot(*plot_2_data)
        self.plot_canvas3.plot(plot1_data, "Energy Per Unit Solar Panel Area", "J/m^2")

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)
        self.refresh_timer.stop()

    def _on_plot_refresh_finished(self, success: bool):
        if not success:
            self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name):
        message1 = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message1)

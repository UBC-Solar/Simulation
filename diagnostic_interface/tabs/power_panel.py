import traceback
from data_tools.query import SunbeamClient
from data_tools.schema import UnwrappedError
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, RealtimeCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout
import numpy as np
from diagnostic_interface.widgets import TimedMapPlot


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)


class PlotRefreshWorker(QRunnable):
    def __init__(self, power_canvas: RealtimeCanvas):
        super().__init__()
        self.signals = PlotRefreshWorkerSignals()
        self.power_canvas = power_canvas

    def run(self):
        try:
            client = SunbeamClient(settings.sunbeam_api_url)
            pipeline = settings.realtime_pipeline
            event = settings.realtime_event

            motor_power = self.power_canvas.fetch_data()

            gps_longitude = client.get_file(pipeline, event, "localization", "GPSLongitude")
            gps_latitude = client.get_file(pipeline, event, "localization", "GPSLatitude")

            self.signals.data_ready.emit(motor_power, gps_longitude, gps_latitude)

        except Exception as e:
            print(e)
            self.signals.error.emit(str(e))


class PowerTab(QWidget):
    def __init__(self, font_size: int = 36, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.layout = QVBoxLayout()

        # First plot: Power vs Time
        self.power_canvas = RealtimeCanvas("power", "MotorPower")
        power_toolbar = CustomNavigationToolbar(self.power_canvas, self)

        self.layout.addWidget(power_toolbar)
        self.layout.addWidget(self.power_canvas, stretch=1)

        self.map_plot_panel = TimedMapPlot(font_size, lambda x: x * x.period,
                                           lambda x: f"Total Energy: {np.sum(x) / 1e3:.1f} kJ")
        self.layout.addWidget(self.map_plot_panel, stretch=3)

        self.line = None

        self.setLayout(self.layout)

        QTimer.singleShot(0, self.refresh_plot)

        self.pool = QThreadPool()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)

        self.motor_power = None
        self.max_laps = None
        self.start_time = None
        self.end_time = None
        self.current_lap_number = 36
        self.time_difference = 60
        self.date = None

    def refresh_plot(self):
        worker = PlotRefreshWorker(self.power_canvas)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self.pool.start(worker)

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.timer.setInterval(settings.plot_timer_interval * 1000)
            self.timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.timer.stop()

    @pyqtSlot(object, object, object)
    def _on_data_ready(self, motor_power, gps_longitude_result, gps_latitude_result):
        try:
            self.motor_power = motor_power

            self.map_plot_panel.set_data(motor_power, gps_latitude_result, gps_longitude_result)

            self.power_canvas.plot(self.motor_power, "Motor Power", "Power (W)")

        except UnwrappedError as e:
            traceback.print_exc()
            QMessageBox.critical(
                self.parent,
                "Power Tab Error",
                f"Failed to load power plots.\n\n{str(e)}"
            )

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)
        self.timer.stop()

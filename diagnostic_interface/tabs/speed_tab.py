from data_tools.query import SunbeamClient
from data_tools.schema import UnwrappedError
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
from diagnostic_interface import settings
from PyQt5.QtWidgets import QWidget, QVBoxLayout
import numpy as np
from diagnostic_interface.widgets import TimedMapPlot


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)


class PlotRefreshWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            client = SunbeamClient(settings.sunbeam_api_url)
            pipeline = settings.realtime_pipeline
            event = settings.realtime_event

            speed = client.get_file(pipeline, event, "cleanup", "SpeedMPS")

            gps_longitude = client.get_file(pipeline, event, "localization", "GPSLongitude")
            gps_latitude = client.get_file(pipeline, event, "localization", "GPSLatitude")

            self.signals.data_ready.emit(speed, gps_longitude, gps_latitude)

        except Exception as e:
            print(e)
            self.signals.error.emit(str(e))


class SpeedTab(QWidget):
    def __init__(self, font_size: int = 36, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.layout = QVBoxLayout()

        self.map_plot_panel = TimedMapPlot(12, lambda x: x, lambda x: f"Average Speed: {np.mean(x):.1f} km/h", horizontal=False)

        self.layout.addWidget(self.map_plot_panel, stretch=3)

        self.setLayout(self.layout)

        QTimer.singleShot(0, self.refresh_plot)

        self.pool = QThreadPool()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)

        self.motor_power = None

    def refresh_plot(self):
        worker = PlotRefreshWorker()
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
    def _on_data_ready(self, speed_result, gps_longitude_result, gps_latitude_result):
        try:
            speed = speed_result.unwrap().data
            self.map_plot_panel.set_data(speed, gps_latitude_result, gps_longitude_result)

        except UnwrappedError:
            pass

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        self.timer.stop()

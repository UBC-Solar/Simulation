from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, SocCanvas


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object)  # emits the TimeSeries
    error = pyqtSignal(str)  # emits an error message


class PlotRefreshWorker(QRunnable):
    def __init__(self, canvas: SocCanvas):
        super().__init__()
        self.canvas: SocCanvas = canvas
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            ts = self.canvas.fetch_data()
            self.signals.data_ready.emit(ts)

        except Exception as e:
            self.signals.error.emit(str(e))


class SOCTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.origin = settings.realtime_pipeline
        self.source = "energy"
        self.event = settings.realtime_event
        self.data_name = "SOC"

        self.pool = QThreadPool()
        self.layout = QVBoxLayout(self)
        self.canvas = SocCanvas(self)
        self.toolbar = CustomNavigationToolbar(canvas=self.canvas)
        self.layout.addWidget(self.toolbar)

        self.layout.addWidget(self.canvas)

        # one-off & repeating timer, interval in milliseconds
        QTimer.singleShot(0, self.refresh_plot)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)
        self.timer.start(settings.plot_timer_interval * 1000)

    def refresh_plot(self):
        worker = PlotRefreshWorker(self.canvas)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self.pool.start(worker)

    @pyqtSlot(object)
    def _on_data_ready(self, ts):
        self.canvas.plot(ts, f"{self.data_name} - {self.event}", self.data_name)

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)

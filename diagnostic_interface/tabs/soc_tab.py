from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, RealtimeCanvas


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object, object)  # emits the TimeSeries
    error = pyqtSignal(str)  # emits an error message


class PlotRefreshWorker(QRunnable):
    def __init__(self, soc_canvas: RealtimeCanvas, unfiltered_soc_canvas: RealtimeCanvas):
        super().__init__()
        self.soc_canvas: RealtimeCanvas = soc_canvas
        self.unfiltered_soc_canvas: RealtimeCanvas = unfiltered_soc_canvas
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            soc = self.soc_canvas.fetch_data()
            unfiltered_soc = self.unfiltered_soc_canvas.fetch_data()
            self.signals.data_ready.emit(soc, unfiltered_soc)

        except Exception as e:
            print(e)
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
        self.soc_canvas = RealtimeCanvas("energy", "SOC")
        self.unfiltered_soc_canvas = RealtimeCanvas("energy", "UnfilteredSOC")
        self.soc_toolbar = CustomNavigationToolbar(canvas=self.soc_canvas)
        self.unfiltered_soc_toolbar = CustomNavigationToolbar(canvas=self.unfiltered_soc_canvas)

        self.layout.addWidget(self.soc_toolbar)
        self.layout.addWidget(self.soc_canvas)

        self.layout.addWidget(self.unfiltered_soc_toolbar)
        self.layout.addWidget(self.unfiltered_soc_canvas)

        # one-off & repeating timer, interval in milliseconds
        QTimer.singleShot(0, self.refresh_plot)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)
        self.timer.start(settings.plot_timer_interval * 1000)

    def refresh_plot(self):
        worker = PlotRefreshWorker(self.soc_canvas, self.unfiltered_soc_canvas)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self.pool.start(worker)

    @pyqtSlot(object, object)
    def _on_data_ready(self, soc, unfiltered_soc):
        self.soc_canvas.plot(soc, f"SOC", "SOC (%)")
        self.unfiltered_soc_canvas.plot(unfiltered_soc, f"Unfiltered SOC", "SOC (%)")

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)

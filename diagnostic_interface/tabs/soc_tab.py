from datetime import datetime, timedelta

from PyQt5.QtWidgets import QMessageBox, QTextEdit
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, RealtimeCanvas
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from data_tools.collections import TimeSeries
from PyQt5.QtGui import QPalette, QColor


class PercentageWidget(QWidget):
    def __init__(self, label_text: str = "", font_size: int = 16, font_size_text: int = 36, parent=None):
        super().__init__(parent)

        self.font_size = font_size
        self.font_size_text = font_size_text

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Text label
        self.text_label = QLabel(label_text)
        text_font = QFont()
        text_font.setPointSize(self.font_size)
        text_font.setBold(True)
        self.text_label.setFont(text_font)

        layout.addWidget(self.text_label, alignment=Qt.AlignVCenter)

        self.percent_label = QLabel("0%")
        pct_font = QFont()
        pct_font.setPointSize(self.font_size)
        pct_font.setBold(True)
        self.percent_label.setFont(pct_font)
        layout.addWidget(self.percent_label, alignment=Qt.AlignVCenter)

        self.set_percentage(0)

    def set_percentage(self, value: float, is_delta: bool = False):
        pct = value
        text = f"{pct:.1f}%"
        self.percent_label.setText(text)

        font = QFont()
        font.setPointSize(self.font_size)
        font.setBold(True)
        self.percent_label.setFont(font)

        text_font = QFont()
        text_font.setPointSize(self.font_size_text)
        text_font.setBold(True)
        self.text_label.setFont(text_font)

        # Choose color
        if not is_delta:
            if pct < 20:
                color = "#e74c3c"  # red
            elif pct < 50:
                color = "#e67e22"  # orange
            else:
                color = "#27ae60"  # green
        else:
            if pct < -15:
                color = "#e74c3c"  # red
            elif -15 <= pct < -5:
                color = "#e67e22"  # orange
            else:
                color = "#27ae60"  # green

        self.percent_label.setStyleSheet(
            f"color: {color};"
            f" font-size: {self.font_size}pt;"
            f" font-weight: bold;"
        )


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

        self.upper_plot_layout = QVBoxLayout()

        self.upper_plot_layout.addWidget(self.soc_toolbar)
        self.upper_plot_layout.addWidget(self.soc_canvas)

        self.layout.addLayout(self.upper_plot_layout, stretch=3)

        self.lower_layout = QHBoxLayout()

        self.lower_plot_layout = QVBoxLayout()
        self.lower_plot_layout.addWidget(self.unfiltered_soc_toolbar)
        self.lower_plot_layout.addWidget(self.unfiltered_soc_canvas)

        self.lower_layout.addLayout(self.lower_plot_layout, stretch=3)

        self.text_layout = QVBoxLayout()

        self.text_widget1 = PercentageWidget("Initial SOC:", font_size=64, font_size_text=36)
        self.text_widget2 = PercentageWidget("Current SOC:", font_size=64, font_size_text=36)
        self.text_widget3 = PercentageWidget("SOC Change (1 hr): ", font_size=64, font_size_text=36)

        self.text_layout.addWidget(self.text_widget1)
        self.text_layout.addWidget(self.text_widget2)
        self.text_layout.addWidget(self.text_widget3)

        self.lower_layout.addLayout(self.text_layout, stretch=2)

        self.layout.addLayout(self.lower_layout, stretch=2)

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
    def _on_data_ready(self, soc: TimeSeries, unfiltered_soc):
        self.soc_canvas.plot(soc, f"SOC", "SOC (%)")
        self.unfiltered_soc_canvas.plot(unfiltered_soc, f"Unfiltered SOC", "SOC (%)")

        initial_soc = soc[0] * 100
        current_soc = soc[-1] * 100

        time_now = soc.datetime_x_axis[-1]
        time_1hr_ago = time_now - timedelta(hours=1)
        time_1hr_ago_relative = time_1hr_ago.timestamp() - soc.datetime_x_axis[0].timestamp()

        index_1hr_ago = soc.index_of(time_1hr_ago_relative)
        soc_1hr_ago = soc[index_1hr_ago] * 100

        self.text_widget1.set_percentage(initial_soc)
        self.text_widget2.set_percentage(current_soc)
        self.text_widget3.set_percentage(soc_1hr_ago - current_soc, is_delta=True)

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)

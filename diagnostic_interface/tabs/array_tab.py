from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QMessageBox
)
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot

from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient
import mplcursors


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object)
    error = pyqtSignal(str)


HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

EVENT = "FSGP_2024_Day_1"


class ArrayPlot(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

        self.current_data = None
        self.current_data2 = None

        self.line1 = None
        self.line2 = None

    def plot(self, data, data2):
        try:

            self.current_data = data
            self.current_data2 = data2

            if self.line1 is None and self.line2 is None:
                self.line1, = self.ax.plot(data.datetime_x_axis, data, linewidth=1, color='red')

                self.ax2 = self.ax.twinx()
                self.line2, = self.ax2.plot(data2.datetime_x_axis, data2, linewidth=1)

                self.ax.set_title("Array Power and Irradiance", fontsize=12)
                self.ax.set_xlabel("Time", fontsize=10)
                self.ax.set_ylabel("Power (W)", fontsize=10)
                self.ax2.set_ylabel("Irradiance (W/m^2)", fontsize=10)

                self.ax.legend([self.line1, self.line2], ["Array Power", "GHI"])

                locator = mdates.AutoDateLocator()
                formatter = mdates.ConciseDateFormatter(locator)
                self.ax.xaxis.set_major_locator(locator)
                self.ax.xaxis.set_major_formatter(formatter)

            else:
                # Only update data
                self.line1.set_xdata(data.datetime_x_axis)
                self.line2.set_xdata(data2.datetime_x_axis)
                self.line1.set_ydata(data)
                self.line2.set_ydata(data2)

            self.ax.relim()
            self.ax.autoscale_view(scalex=True, scaley=True)

            self.ax2.relim()
            self.ax2.autoscale_view(scalex=True, scaley=True)

            self.fig.tight_layout()
            self.draw()

            cursor = mplcursors.cursor([self.line1, self.line2], hover=True)

            @cursor.connect("add")
            def _(sel):
                x, y = sel.target  # x is a float (matplotlib date), y is the y-value
                dt = mdates.num2date(x)
                sel.annotation.set_text(
                    f"{y:.2f} at {dt.strftime('%H:%M')}"
                )
                # optional: tweak annotation style
                bbox = sel.annotation.get_bbox_patch()
                bbox.set_facecolor("white")
                bbox.set_edgecolor("black")
                bbox.set_alpha(0.8)
                bbox.set_boxstyle("round,pad=0.3")

            return True

        except Exception as e:
            QMessageBox.critical(None, "Plotting Error", f"Error fetching or plotting data:\n{str(e)}")
            return False

    def fetch_data(self):
        data = self.query_data(settings.realtime_pipeline, "array", settings.realtime_event, "ArrayPower")
        data2 = self.query_data(settings.realtime_pipeline, "weather", settings.realtime_event, "GHI")

        return data, data2

    def query_data(self, origin, source, event, data_name):
        client = SunbeamClient(settings.sunbeam_api_url)
        file = client.get_file(origin, event, source, data_name)
        result = file.unwrap()
        return result.values if hasattr(result, "values") else result.data

    def save_data_to_csv(self):
        pass


class PlotRefreshWorker(QRunnable):
    def __init__(self, array_plot: ArrayPlot):
        super().__init__()
        self.array_plot: ArrayPlot = array_plot
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            array_plot_data = self.array_plot.fetch_data()
            self.signals.data_ready.emit(array_plot_data)

        except Exception as e:
            self.signals.error.emit(str(e))


class ArrayTab(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)
        self._thread_pool = QThreadPool()

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(30, 30, 30, 30)

        self.plot_canvas2 = ArrayPlot()
        self.toolbar2 = CustomNavigationToolbar(canvas=self.plot_canvas2)

        self.layout.addWidget(self.toolbar2)
        self.layout.addWidget(self.plot_canvas2)

        self.setLayout(self.layout)

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

        worker = PlotRefreshWorker(self.plot_canvas2)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self._thread_pool.start(worker)

    @pyqtSlot(object)
    def _on_data_ready(self, plot_2_data):
        self.plot_canvas2.plot(*plot_2_data)

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)
        self.refresh_timer.stop()

    def _on_plot_refresh_finished(self, success: bool):
        pass

    def show_help_message(self, data_name):
        message1 = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message1)


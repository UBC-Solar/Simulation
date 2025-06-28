import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient, TimeSeries
from diagnostic_interface import settings
from PyQt5.QtWidgets import QMessageBox
import mplcursors


plt.style.use("seaborn-v0_8-darkgrid")


class RealtimeCanvas(FigureCanvas):
    def __init__(self, source: str, data_name: str, parent=None):
        fig = Figure(figsize=(5, 3))
        super().__init__(fig)

        self.source = source
        self.data_name = data_name

        self.setParent(parent)
        self.ax = fig.add_subplot(111)
        self.line = None

    def fetch_data(self) -> TimeSeries:
        client = SunbeamClient(settings.sunbeam_api_url)
        file = client.get_file(settings.realtime_pipeline, settings.realtime_event, self.source, self.data_name)
        result = file.unwrap()

        return result.values if hasattr(result, "values") else result.data

    def plot(self, ts: TimeSeries, title: str, y_label: str) -> None:
        x = ts.datetime_x_axis
        y = ts

        if self.line is None:
            self.line, = self.ax.plot(x, y, linewidth=1)
            self.ax.set_title(title)
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel(y_label)

            locator = mdates.AutoDateLocator()
            formatter = mdates.ConciseDateFormatter(locator)
            self.ax.xaxis.set_major_locator(locator)
            self.ax.xaxis.set_major_formatter(formatter)

        else:
            self.line.set_xdata(x)
            self.line.set_ydata(y)

        self.ax.relim()
        self.ax.autoscale_view(scalex=True, scaley=True)
        self.draw()

        cursor = mplcursors.cursor(self.line, hover=True)

        @cursor.connect("add")
        def _(sel):
            x, y = sel.target  # x is a float (matplotlib date), y is the y-value
            dt = mdates.num2date(x)
            sel.annotation.set_text(
                f"{y:.2f} {ts.units} at {dt.strftime('%H:%M')}"
            )
            # optional: tweak annotation style
            bbox = sel.annotation.get_bbox_patch()
            bbox.set_facecolor("white")
            bbox.set_edgecolor("black")
            bbox.set_alpha(0.8)
            bbox.set_boxstyle("round,pad=0.3")

    def save_data_to_csv(self):
        QMessageBox.warning(self, "Cannot save data from here! Please plot manually with the Home Tab.")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient, TimeSeries
from diagnostic_interface import settings
from PyQt5.QtWidgets import QMessageBox
import mplcursors
from dateutil import tz


plt.style.use("seaborn-v0_8-darkgrid")
local_tz = tz.tzlocal()


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
        file = client.get_file(
            settings.realtime_pipeline,
            settings.realtime_event,
            self.source,
            self.data_name
        )
        result = file.unwrap()
        return result.values if hasattr(result, "values") else result.data

    def plot(self, ts: TimeSeries, title: str, y_label: str) -> None:
        x = ts.datetime_x_axis
        y = ts

        if self.line is None:
            # Tell AutoDateLocator that the source tz is UTC and make the formatter display in local time
            locator = mdates.AutoDateLocator(tz=local_tz)
            formatter = mdates.ConciseDateFormatter(locator, tz=local_tz)

            self.line, = self.ax.plot(x, y, linewidth=1)
            self.ax.set_title(title)
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel(y_label)

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
            xdate, yval = sel.target
            # Interpret xdate as UTC, then convert to local
            dt_utc = mdates.num2date(xdate, tz=local_tz)
            dt_local = dt_utc.astimezone(local_tz)
            sel.annotation.set_text(
                f"{yval:.2f} {ts.units} at {dt_local.strftime('%H:%M:%S')}"
            )
            bbox = sel.annotation.get_bbox_patch()
            bbox.set_facecolor("white")
            bbox.set_edgecolor("black")
            bbox.set_alpha(0.8)
            bbox.set_boxstyle("round,pad=0.3")

    def save_data_to_csv(self):
        QMessageBox.warning(
            self,
            "Cannot save data from here!",
            "Please plot manually with the Home Tab."
        )

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient, TimeSeries
from scipy.integrate import cumulative_trapezoid as trapz
from diagnostic_interface import settings
from typing import Optional
import mplcursors
from dateutil import tz

plt.style.use("seaborn-v0_8-darkgrid")
local_tz = tz.tzlocal()


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

        self.current_data: Optional[TimeSeries] = None

        self.line = None

    def fetch_data(self, origin: str, event: str, source: str, data_name: str) -> TimeSeries:
        client = SunbeamClient(settings.sunbeam_api_url)
        file = client.get_file(origin, event, source, data_name)
        result = file.unwrap()

        data = result.values if hasattr(result, "values") else result.data
        self.current_data = data

        return data

    def plot(self, ts: TimeSeries, title: str, y_label: str) -> None:
        x = ts.datetime_x_axis
        y = ts

        if self.line is None:
            self.line, = self.ax.plot(x, y, linewidth=1)
            self.ax.set_title(title)
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel(y_label)

            locator = mdates.AutoDateLocator()
            formatter = mdates.DateFormatter("%H:%M", tz=local_tz)

            self.ax.xaxis.set_major_formatter(formatter)
            self.ax.xaxis.set_major_locator(locator)

            self.figure.autofmt_xdate()

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
            dt = mdates.num2date(x, tz=local_tz)
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
        if self.current_data is None:
            print("No data available to save.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            None,
            "Save Data",
            f"{self.current_data_name}_{self.current_event}_{self.current_origin}_{self.current_source}.csv",
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )

        if file_name:
            df = pd.DataFrame({
                "Time": self.current_data.datetime_x_axis,
                f"{self.current_data_name}": self.current_data,
            })
            df.to_csv(file_name, index=False)
            print(f"Data saved to {file_name}")


class PlotCanvas2(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

        self.current_data = None
        self.current_data_name = ""
        self.current_event = ""
        self.current_origin = ""
        self.current_source = ""

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

                #self.ax.set_title(f"{data_name} - {event}", fontsize=12)
                self.ax.set_title("Wind Speed and Precipitation", fontsize=12)
                self.ax.set_xlabel("Time", fontsize=10)
                self.ax.set_ylabel("WindSpeed10m", fontsize=10)
                self.ax2.set_ylabel("PrecipitationRate", fontsize=10)

                self.ax.legend([self.line1, self.line2], ["Wind Speed", "Precipitation Rate"])

                locator = mdates.AutoDateLocator()
                formatter = mdates.DateFormatter("%H:%M", tz=local_tz)

                self.ax.xaxis.set_major_formatter(formatter)
                self.ax.xaxis.set_major_locator(locator)

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
                dt = mdates.num2date(x, tz=local_tz)
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
        data = self.query_data(settings.realtime_pipeline, "weather", settings.realtime_event, "WindSpeed10m")
        data2 = self.query_data(settings.realtime_pipeline, "weather", settings.realtime_event, "PrecipitationRate")

        return data, data2

    def query_data(self, origin, source, event, data_name):
        client = SunbeamClient(settings.sunbeam_api_url)
        file = client.get_file(origin, event, source, data_name)
        result = file.unwrap()
        return result.values if hasattr(result, "values") else result.data

    def save_data_to_csv(self):
        if self.current_data is None:
            print("No data available to save.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            None,
            "Save Data",
            f"{self.current_data_name}_{self.current_event}_{self.current_origin}_{self.current_source}.csv",
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )

        if file_name:
            df = pd.DataFrame({
                "Time": self.current_data.datetime_x_axis,
                f"{self.current_data_name}": self.current_data,
            })
            df.to_csv(file_name, index=False)
            print(f"Data saved to {file_name}")


class IntegralPlot(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

        self.current_data = None
        self.line1 = None

    def plot(self, data, plot_title, ylabel):

        try:
            integral_values = trapz(data, x=data.x_axis, initial=0)

            if not isinstance(data, TimeSeries):
                raise TypeError("Expected TimeSeries.")

            self.current_data = None
            self.line1 = None

            if self.line1 is None:

                self.line1, = self.ax.plot(data.datetime_x_axis, integral_values, linewidth=1, color='red')
                #add the comma so that its not just a normal 2d plot

                #self.ax.set_title(f"{data_name} - {event}", fontsize=12)
                self.ax.set_title(plot_title, fontsize=12)
                self.ax.set_xlabel("Time", fontsize=10)
                self.ax.set_ylabel(ylabel, fontsize=10)

                # Improve datetime formatting
                locator = mdates.AutoDateLocator()
                formatter = mdates.DateFormatter("%H:%M", tz=local_tz)

                self.ax.xaxis.set_major_formatter(formatter)
                self.ax.xaxis.set_major_locator(locator)

            else:
                # Only update data
                self.line1.set_xdata(data.datetime_x_axis)

                self.line1.set_ydata(integral_values)

            self.ax.relim()
            self.ax.autoscale_view(scalex=True, scaley=True)

            self.fig.tight_layout()
            self.draw()

            cursor = mplcursors.cursor(self.line1, hover=True)

            @cursor.connect("add")
            def _(sel):
                x, y = sel.target  # x is a float (matplotlib date), y is the y-value
                dt = mdates.num2date(x, tz=local_tz)
                sel.annotation.set_text(
                    f"{y/1e6:.2f} MJ/m^2 at {dt.strftime('%H:%M')}"
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

    def query_data(self, origin, source, event, data_name):
        client = SunbeamClient(settings.sunbeam_api_url)
        file = client.get_file(origin, event, source, data_name)
        result = file.unwrap()
        return result.values if hasattr(result, "values") else result.data

    def save_data_to_csv(self):
        if self.current_data is None:
            print("No data available to save.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            None,
            "Save Data",
            f"{self.current_data_name}_{self.current_event}_{self.current_origin}_{self.current_source}.csv",

            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )

        if file_name:
            df = pd.DataFrame({
                "Time": self.current_data.datetime_x_axis,
                f"{self.current_data_name}": self.current_data,
            })
            df.to_csv(file_name, index=False)
            print(f"Data saved to {file_name}")

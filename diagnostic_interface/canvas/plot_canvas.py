import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient, TimeSeries
from diagnostic_interface import settings
from typing import Optional


plt.style.use("seaborn-v0_8-darkgrid")


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
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            self.ax.xaxis.set_major_locator(mdates.HourLocator())
            self.figure.autofmt_xdate()

        else:
            self.line.set_xdata(x)
            self.line.set_ydata(y)

        self.ax.relim()
        self.ax.autoscale_view(scalex=True, scaley=True)
        self.draw()

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

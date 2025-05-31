import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient, TimeSeries
from diagnostic_interface import settings

# Use a light-theme friendly style
plt.style.use("seaborn-v0_8-darkgrid")
# plt.style.use("fivethirtyeight")


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)

        self.current_data = None
        self.current_data_name = ""
        self.current_event = ""
        self.current_origin = ""
        self.current_source = ""

        self.line = None

    def query_and_plot(self, origin, source, event, data_name):
        try:
            data = self.query_data(origin, source, event, data_name)
            if not isinstance(data, TimeSeries):
                raise TypeError("Expected TimeSeries.")

            self.current_data = data
            self.current_data_name = data_name
            self.current_event = event
            self.current_origin = origin
            self.current_source = source

            if self.line is None:
                self.line, = self.ax.plot(data.datetime_x_axis, data, linewidth=1)
                self.ax.set_title(f"{data_name} - {event}", fontsize=12)
                self.ax.set_xlabel("Time", fontsize=10)
                self.ax.set_ylabel(data_name, fontsize=10)

                # Improve datetime formatting
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(mdates.HourLocator())
                self.fig.autofmt_xdate()

            else:
                # Only update data
                self.line.set_xdata(data.datetime_x_axis)
                self.line.set_ydata(data)

            self.ax.relim()
            self.ax.autoscale_view(scalex=True, scaley=True)
            self.fig.tight_layout()
            self.draw()

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






#temp:


class PlotCanvas2(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(figsize = (width, height))
        super().__init__(self.fig)
        self.setParent(parent)

        self.current_data = None
        self.current_data_name = ""
        self.current_event = ""
        self.current_origin = ""
        self.current_source = ""

        self.line = None

    def query_and_plot(self, origin, source, event, data_name):
        try:
            data = self.query_data(origin, source, event, data_name)
            if not isinstance(data, TimeSeries):
                raise TypeError("Expected TimeSeries.")

            self.current_data = data
            self.current_data_name = data_name
            self.current_event = event
            self.current_origin = origin
            self.current_source = source

            if self.line is None:
                self.line, = self.ax.plot(data.datetime_x_axis, data, linewidth=1)
                self.ax.set_title(f"{data_name} - {event}", fontsize=12)
                self.ax.set_xlabel("Time", fontsize=10)
                self.ax.set_ylabel(data_name, fontsize=10)

                # Improve datetime formatting
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(mdates.HourLocator())
                self.fig.autofmt_xdate()

            else:
                # Only update data
                self.line.set_xdata(data.datetime_x_axis)
                self.line.set_ydata(data)

            self.ax.relim()
            self.ax.autoscale_view(scalex=True, scaley=True)
            self.fig.tight_layout()
            self.draw()

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

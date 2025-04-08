import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data_tools import SunbeamClient, TimeSeries


class PlotCanvas(FigureCanvas):
    """A PlotCanvas is the space on which we insert our toolbar
    and our plots."""
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        self.current_data = None

    def query_and_plot(self, origin, source, event, data_name):
        """
        This method calls on query_data and then plots the data returned.

        :param str origin: pipeline name
        :param str source: pipeline stage
        :param str event: race type and race day.
        :param str data_name: the type of data that is being queried (e.g. Vehicle_Velocity).
        :raises TypeError: if the data is not a TimeSeries
        :returns bool: depending on whether it was possible to query and plot the data
        """
        try:
            data = self.query_data(origin, source, event, data_name)
            if not isinstance(data, TimeSeries):
                raise TypeError("Expected TimeSeries.")

            self.current_data = data
            self.current_data_name = data_name
            self.current_event = event
            self.current_origin = origin
            self.current_source = source
            self.ax.clear()
            self.ax.plot(data.datetime_x_axis, data)
            self.ax.set_title(f"{data_name} - {event}")
            self.draw()
        except Exception as e:
            QMessageBox.critical(
                None, "Plotting Error", f"Error fetching or plotting data:\n{str(e)}"
            )

    def query_data(self, origin, source, event, data_name):
        """
        This method queries data from SunBeam as a file, and later unwraps it.

        :param str origin: pipeline name
        :param str source: pipeline stage
        :param str event: race type and race day.
        :param str data_name: the type of data that is being queried (e.g. Vehicle_Velocity).
        :raises ValueError: if it is not possible to extract data from the queried file.
        :returns: a TimeSeries with the values you wanted to query.
        """
        client = SunbeamClient()
        file = client.get_file(origin, event, source, data_name)
        result = file.unwrap()
        return result.values if hasattr(result, "values") else result.data

    def refresh_plot(self):
        """Updates current plot by rerunning query_and_plot."""
        self.query_and_plot(
            self.current_origin,
            self.current_source,
            self.current_event,
            self.current_data_name,
        )

    def save_data_to_csv(self):
        """
        Saves the current data as a CSV file.
        """
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
            df = pd.DataFrame(
                {
                    "Time (s)": range(len(self.current_data)),
                    f"{self.current_data_name}": self.current_data,
                }
            )
            df.to_csv(file_name, index=False)
            print(f"Data saved to {file_name}")

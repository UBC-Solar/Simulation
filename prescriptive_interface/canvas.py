from PyQt5.QtWidgets import QVBoxLayout, QSizePolicy, QDialog, QWidget
from PyQt5.QtCore import QSize
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import os
import tempfile
from PyQt5.QtCore import QUrl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import mplcursors
from prescriptive_interface import SettingsDialog
import itertools


class SimulationCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.fig = plt.Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.fig)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: none; border: none;")
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_simulation_results(self, results_dict):
        self.fig.clear()
        self.fig.set_constrained_layout(True)

        axes = self.fig.subplots(2, 3, sharex=True)

        cmap = plt.get_cmap("tab10")
        color_cycle = itertools.cycle(cmap.colors)

        y_labels = {
            "speed_kmh": "Speed (km/h)",
            "distances": "Distance (km)",
            "state_of_charge": "SOC (%)",
            "delta_energy": "Delta Energy (J)",
            "solar_irradiances": "Solar Irradiance (W/m²)",
            "wind_speeds": "Wind Speed (km/h)",
        }

        titles = {
            "speed_kmh": "Speed",
            "distances": "Distance Travelled",
            "state_of_charge": "State of Charge",
            "delta_energy": "Energy Consumption",
            "solar_irradiances": "Solar Irradiance",
            "wind_speeds": "Wind Speed",
        }

        for ax, (label, (timestamps, data)) in zip(axes.flat, results_dict.items()):
            ax.plot(timestamps, data, color=next(color_cycle), linewidth=1.5)
            ax.set_title(titles[label], loc="left", pad=8)
            ax.set_ylabel(y_labels[label], labelpad=6)

        for ax in axes[0]:
            ax.tick_params(labelbottom=False)

        for ax in axes[1]:
            ax.set_xlabel("Time (s)", fontsize=10)

        self.fig.subplots_adjust(
            left=0.06, right=0.98,
            top=0.93, bottom=0.08,
            hspace=0.35, wspace=0.25
        )

        self.canvas.draw_idle()


class SpeedPlotCanvas(FigureCanvas):
    """Canvas to display the optimized speed graph in the optimization window."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.popsize = 6  # default population size
        self.maxiter = 100  # default number of iterations

    def plot_optimized_speeds(self, base_model, speeds, laps_per_index, num_laps):
        """
        Plot optimized speeds vs laps on the optimization tab.

        :param speeds: The optimized speeds; one per lap.
        :returns: None
        """
        self.ax.clear()

        y = [speed for speed in speeds for _ in
             range(laps_per_index)]  # Make sure that speeds repeat for a certain number of laps
        y = y[:num_laps]
        x = range(1, len(y) + 1)

        [self.line] = self.ax.plot(x, y, marker='o')

        self.ax.set_xlabel("Lap")
        self.ax.set_ylabel("Speed [km/h]")
        self.ax.set_title("Optimized Speed vs Lap")
        self.ax.grid(True)
        self.draw()

        # Adding tooltips on hover
        cursor = mplcursors.cursor(self.line, hover=True)

        @cursor.connect("add")
        def _(sel):
            x, y = sel.target
            sel.annotation.set_text(f"{y:.2f} km/h at lap {int(x)}")

            bbox = sel.annotation.get_bbox_patch()
            bbox.set_facecolor("white")
            bbox.set_edgecolor("black")
            bbox.set_alpha(0.8)
            bbox.set_boxstyle("round,pad=0.3")

    def open_settings(self):
        """
        Opens a settings menu that allows you to change the population size and generation limit of the optimization.
        """
        dialog = SettingsDialog(self.popsize, self.maxiter)
        if dialog.exec_() == QDialog.Accepted:
            popsize, maxiter = dialog.get_values()
            if popsize and maxiter:
                self.popsize = popsize
                self.maxiter = maxiter
                print(f"Updated settings: popsize={popsize}, maxiter={maxiter}")
            else:
                print("Invalid input.")


class FoliumMapWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lap_num = 0
        self.model = None
        self.temp_dir = tempfile.gettempdir()

    def plot_optimized_speeds(self, model):
        """
        Store the optimized model and render it on the Folium map widget.

        :param model: The optimized simulation model containing GIS and speed data.
        :type model: SimulationModel
        :returns: None
        :rtype: None
        """
        self.model = model
        self.update_map()

    def update_lap(self, direction):
        """
        Change the currently displayed lap and refresh the map visualization.

        :param direction: The direction to move in lap navigation ("next" or "prev").
        :type direction: str
        :returns: None
        :rtype: None
        """
        if direction == "next":
            self.lap_num += 1
        elif direction == "prev":
            self.lap_num = max(0, self.lap_num - 1)
        self.update_map()

    def update_map(self):
        if not self.model:
            return

        num_coordinates = int(self.model.gis.num_unique_coords)
        gis_indices, speed_kmh = self.model.get_results(["closest_gis_indices", "speed_kmh"])
        coords = self.model.gis.get_path()

        beginning_coordinate = num_coordinates * self.lap_num
        end_coordinate = num_coordinates * (self.lap_num + 1)
        coords_of_interest = coords[beginning_coordinate:end_coordinate + 1]

        speeds = []

        for i in range(len(coords_of_interest) - 1):
            k = i + beginning_coordinate

            if k >= 288:
                break  # Stop plotting if index exceeds 288 (one lap)

            indices = np.where(gis_indices == k)[0]
            if len(indices) > 0:
                speed = speed_kmh[indices[0]]
            else:
                speed = 0
            speeds.append(speed)

        max_speed = max(speeds) if speeds else 1
        norm = mcolors.Normalize(vmin=0, vmax=max_speed)
        cmap = cm.get_cmap('YlOrRd')

        # Create map
        fmap = folium.Map(location=coords_of_interest[0], zoom_start=14)
        for i in range(len(speeds)):
            speed = speeds[i]
            color = mcolors.to_hex(cmap(norm(speed)))

            folium.PolyLine(
                locations=[coords_of_interest[i], coords_of_interest[i + 1]],
                color=color,
                weight=5,
                tooltip=f"{speed:.1f} km/h",
                popup=f"Segment speed: {speed:.1f} km/h"
            ).add_to(fmap)

        # Save and display
        filepath = os.path.join(self.temp_dir, "optimized_route_map.html")
        fmap.save(filepath)
        self.load(QUrl.fromLocalFile(filepath))

from PyQt5.QtWidgets import QVBoxLayout, QSizePolicy, QDialog
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


class SimulationCanvas(FigureCanvas):
    """Canvas to display multiple simulation plots dynamically with better formatting."""

    def __init__(self, parent=None):
        self.fig, self.axes = plt.subplots(2, 3, figsize=(16, 12))  # Increased figure size
        super().__init__(self.fig)
        self.setParent(parent)
        # Create a Matplotlib Canvas
        self.canvas = FigureCanvas(self.fig)

        # Add Navigation Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: none; border: none;")
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)  # Prevent expanding into plots
        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)  # Add margins for proper spacing
        self.setLayout(layout)

    def plot_simulation_results(self, results_dict):
        """
       Plot simulation results across a 3x3 grid of subplots.

       This method takes a dictionary of simulation result data where each key maps to a (timestamps, values) tuple.
       Each subplot displays a single result over time with appropriate axis labels, titles, and legends.

       :param results_dict: A dictionary mapping result labels to (timestamps, data) tuples.
                            Example: {"speed_kmh": ([...timestamps...], [...values...]), ...}
       :type results_dict: dict
       :returns: None
       :rtype: None
       """
        self.fig.clear()  # Clear previous plots
        axes = self.fig.subplots(2, 3)  # Regenerate subplots with better spacing
        y_labels = {
            "speed_kmh": "Speed (km/h)",
            "distances": "Distance (km)",
            "state_of_charge": "SOC (%)",
            "delta_energy": "Delta Energy (J)",
            "solar_irradiances": "Solar Irradiance (W/m²)",
            "wind_speeds": "Wind Speed (km/h)"
        }

        for ax, (label, (timestamps, data)) in zip(axes.flat, results_dict.items()):
            ax.plot(timestamps, data, label=label)
            ax.set_title(label, fontsize=12, loc="left", pad=10)  # Add spacing below title
            ax.set_xlabel("Time (s)", fontsize=10, loc="right", labelpad=5)
            ax.legend(fontsize=9)
            ax.set_ylabel(y_labels.get(label, "Value"), fontsize=10, fontweight='normal', labelpad=5)

        # Adjust subplot spacing to avoid overlap
        self.fig.tight_layout(pad=2.0)
        self.fig.subplots_adjust(hspace=0.4, wspace=0.3)  # Add horizontal & vertical spacing

        self.fig.canvas.draw_idle()


class SpeedPlotCanvas(FigureCanvas):
    """Canvas to display the optimized speed graph in the optimization window."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.popsize = 6  # default population size
        self.maxiter = 100  # default number of iterations

    def plot_optimized_speeds(self, speeds, laps_per_index):
        """
        Plot optimized speeds vs laps on the optimization tab.

        :param speeds: The optimized speeds; one per lap.
        :returns: None
        """
        self.ax.clear()

        y = [speed for speed in speeds for _ in
             range(laps_per_index)]  # Make sure that speeds repeat for a certain number of laps
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

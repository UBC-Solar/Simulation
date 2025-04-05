import random
import string
import sys
from typing import Optional
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QProgressBar, QTabWidget, \
    QSizePolicy
from PyQt5.QtCore import QThread, pyqtSignal, QSize
from simulation.cmd import run_simulation
from simulation.cmd.run_simulation import SimulationSettings, build_model
from simulation.config import speeds_directory
from simulation.optimization.genetic import GeneticOptimization, OptimizationSettings
from simulation.utils import InputBounds
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

class SimulationCanvas(FigureCanvas):
    """Canvas to display multiple simulation plots dynamically with better formatting."""

    def __init__(self, parent=None):
        self.fig, self.axes = plt.subplots(3, 3, figsize=(16, 12))  # Increased figure size
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
        axes = self.fig.subplots(3, 3)  # Regenerate subplots with better spacing
        y_labels = {
            "speed_kmh": "Speed (km/h)",
            "distances": "Distance (km)",
            "state_of_charge": "SOC (%)",
            "delta_energy": "Delta Energy (J)",
            "solar_irradiances": "Solar Irradiance (W/m²)",
            "wind_speeds": "Wind Speed (km/h)",
            "gis_route_elevations_at_each_tick": "Elevation (m)",
            "raw_soc": "Raw SOC (%)",
        }

        for ax, (label, (timestamps, data)) in zip(axes.flat, results_dict.items()):
            ax.plot(timestamps, data, label=label)
            ax.set_title(label, fontsize=12, loc="left", pad=10)  # Add spacing below title
            ax.set_xlabel("Time (s)", fontsize=10, loc="right", labelpad=5)
            ax.legend(fontsize=9)
            ax.set_ylabel(y_labels.get(label, "Value"), fontsize=10, fontweight='normal', labelpad=5)

        # Adjust subplot spacing to avoid overlap
        self.fig.tight_layout(pad=8.0)
        self.fig.subplots_adjust(hspace=0.4, wspace=0.3)  # Add horizontal & vertical spacing

        self.fig.canvas.draw_idle()


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

        # Aggregate average speeds for segments
        mean_speeds = []
        last_known_speed = 0

        for i in range(len(coords_of_interest) - 1):
            k = i + beginning_coordinate
            indices = np.where(gis_indices == k)[0]
            if len(indices) > 0:
                speed = np.mean(speed_kmh[indices])
                mean_speeds.append(speed)
                last_known_speed = speed
            else:
                # Interpolate using the last known speed and look ahead for the next known one
                j = i + 1
                while j < len(coords_of_interest) - 1:
                    future_k = j + beginning_coordinate
                    future_indices = np.where(gis_indices == future_k)[0]
                    if len(future_indices) > 0:
                        future_speed = np.mean(speed_kmh[future_indices])
                        interp_speed = np.linspace(last_known_speed, future_speed, j - i + 1)[1:]
                        mean_speeds.extend(interp_speed)
                        break
                    j += 1
                else:
                    mean_speeds.append(last_known_speed if last_known_speed is not None else 0)

        max_speed = max(mean_speeds) if mean_speeds else 1
        norm = mcolors.Normalize(vmin=0, vmax=max_speed)
        cmap = cm.get_cmap('YlOrRd')

        # Create map
        fmap = folium.Map(location=coords_of_interest[0], zoom_start=14)
        for i in range(len(coords_of_interest) - 1):
            speed = mean_speeds[i]
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


class SimulationThread(QThread):
    update_signal = pyqtSignal(str)
    plot_data_signal = pyqtSignal(dict)  # Send multiple plots as a dictionary

    def __init__(self, settings: SimulationSettings, speeds_filename: Optional[str]):
        super().__init__()
        self.settings = settings
        self.speeds_filename = speeds_filename

    def run(self):
        self.update_signal.emit("Starting simulation...")

        try:
            simulation_model = run_simulation.run_simulation(self.settings, self.speeds_filename, plot_results=False)
            driving_hours = simulation_model.get_driving_time_divisions()
            if self.speeds_filename is None:
                input_speed = np.array([45] * driving_hours)
            else:
                input_speed = np.load(speeds_directory / (self.speeds_filename + ".npy"))
                if len(input_speed) != driving_hours:
                    raise ValueError(f"Cached speeds {self.speeds_filename} has improper length!")
            simulation_model.run_model(
                speed=input_speed, plot_results=False
            )
            # Extract multiple data series
            results_keys = ["timestamps", "speed_kmh", "distances", "state_of_charge",
                            "delta_energy", "solar_irradiances", "wind_speeds",
                            "gis_route_elevations_at_each_tick", "raw_soc"]

            results_values = simulation_model.get_results(results_keys)
            results_dict = {key: (results_values[0], values) for key, values in
                            zip(results_keys[1:], results_values[1:])}

            # Emit all data for plotting
            self.plot_data_signal.emit(results_dict)
            results = simulation_model.get_results(
                ["time_taken", "max_route_distance", "distance_travelled", "speed_kmh", "final_soc"])
            formatted_results = (
                f"Simulation successful!\n"
                f"Time taken: {results[0]}\n"
                f"Route length: {results[1]:.2f}km\n"
                f"Maximum distance traversable: {results[2]:.2f}km\n"
                f"Average speed: {np.average(results[3]):.2f}km/h\n"
                f"Final battery SOC: {results[4]:.2f}%\n"
            )
            self.update_signal.emit(formatted_results)

        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")


class OptimizationThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    model_signal = pyqtSignal(object)  # Emits optimized simulation model


    def __init__(self, settings: SimulationSettings):
        super().__init__()
        self.settings = settings

    def run(self):
        self.update_signal.emit("Starting optimization...")
        try:
            simulation_model = build_model(self.settings)
            # Initialize a "guess" speed array
            driving_hours = simulation_model.get_driving_time_divisions()

            # Set up optimization models
            maximum_speed = 60
            minimum_speed = 0

            bounds = InputBounds()
            bounds.add_bounds(driving_hours, minimum_speed, maximum_speed)
            input_speed = np.array([60] * driving_hours)

            # Run simulation model with the "guess" speed array
            simulation_model.run_model(speed=input_speed, plot_results=False,
                                       verbose=self.settings.verbose,
                                       route_visualization=self.settings.route_visualization)

            # Perform optimization with Genetic Optimization
            optimization_settings: OptimizationSettings = OptimizationSettings()
            optimization_settings.generation_limit = 2  # For testing purposes

            genetic_optimization = GeneticOptimization(
                simulation_model, bounds, settings=optimization_settings, pbar=None,
                progress_signal=self.progress_signal, update_signal=self.update_signal
                # Attach signals so progress bar gets updated
            )

            results_genetic = genetic_optimization.maximize()

            self.progress_signal.emit(100)  # Set progress bar to 100% after completion


            simulation_model.run_model(results_genetic, plot_results=False)

            filename = self.get_random_string(7) + ".npy"
            np.save(speeds_directory / filename, results_genetic)
            self.update_signal.emit(f"Optimization completed successfully! Results saved in: {filename}")
            self.model_signal.emit(simulation_model)

        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")


    def get_random_string(self, length: int) -> str:
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

class SimulationTab(QWidget):
    def __init__(self, run_callback):
        """
        Initialize the SimulationTab widget.

        Sets up internal references and prepares the UI layout for running simulations.
        A callback function is required to handle the simulation logic when the run button is pressed.

        :param run_callback: Function to be called when the simulation run button is clicked.
        :type run_callback: Callable
        :returns: None
        :rtype: None
        """
        super().__init__()
        self.run_callback = run_callback
        self.start_button: Optional[QPushButton] = None
        self.sim_output_text: Optional[QTextEdit] = None
        self.sim_canvas: Optional[SimulationCanvas] = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.start_button = QPushButton("Run Simulation")
        self.start_button.clicked.connect(self.run_callback)
        layout.addWidget(self.start_button)

        self.sim_output_text = QTextEdit()
        self.sim_output_text.setReadOnly(True)
        self.sim_output_text.setFixedHeight(100)
        layout.addWidget(self.sim_output_text)

        self.sim_canvas = SimulationCanvas()
        layout.addWidget(self.sim_canvas)

        self.setLayout(layout)


class OptimizationTab(QWidget):
    def __init__(self, optimize_callback, lap_callback):
        """
        Initialize the OptimizationTab widget.

        Sets up internal UI components for running the simulation optimization and navigating lap segments.
        Requires two callback functions to be passed in for optimization logic and lap navigation.

        :param optimize_callback: Function to be called when the optimization button is clicked.
        :type optimize_callback: Callable
        :param lap_callback: Function to be called when lap navigation buttons are clicked.
        :type lap_callback: Callable
        :returns: None
        :rtype: None
        """
        super().__init__()
        self.optimize_callback = optimize_callback
        self.lap_callback = lap_callback

        self.optimize_button: Optional[QPushButton] = None
        self.output_text: Optional[QTextEdit] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.speed_canvas: Optional[FoliumMapWidget] = None
        self.prev_lap_button: Optional[QPushButton] = None
        self.next_lap_button: Optional[QPushButton] = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.optimize_button = QPushButton("Optimize Simulation")
        self.optimize_button.clicked.connect(self.optimize_callback)
        layout.addWidget(self.optimize_button)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.speed_canvas = FoliumMapWidget(self)
        self.speed_canvas.setMinimumHeight(500)
        self.speed_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.speed_canvas)

        self.prev_lap_button = QPushButton("Previous Lap")
        self.prev_lap_button.clicked.connect(lambda: self.lap_callback("prev"))

        self.next_lap_button = QPushButton("Next Lap")
        self.next_lap_button.clicked.connect(lambda: self.lap_callback("next"))

        nav_layout = QVBoxLayout()
        nav_layout.addWidget(self.prev_lap_button)
        nav_layout.addWidget(self.next_lap_button)
        layout.addLayout(nav_layout)

        self.setLayout(layout)

class SimulationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.tabs: Optional[QTabWidget] = None

        self.simulation_tab: Optional[SimulationTab] = None
        self.optimization_tab: Optional[OptimizationTab] = None
        self.simulation_settings = SimulationSettings(race_type="FSGP", verbose=True, granularity=1)

        self.simulation_thread: Optional[SimulationThread] = None
        self.optimization_thread: Optional[OptimizationThread] = None

        self.init_ui()

    def update_lap(self, direction):
        """
        Trigger an update of the lap display on the speed map widget.

        This method delegates the lap navigation command to the FoliumMapWidget,
        which updates the map view based on the given direction.

        :param direction: Either "next" or "prev", indicating the lap to display.
        :type direction: str
        :returns: None
        :rtype: None
        """
        self.optimization_tab.speed_canvas.update_lap(direction)

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simulation_tab = SimulationTab(run_callback=self.run_simulation)
        self.optimization_tab = OptimizationTab(
            optimize_callback=self.optimize_simulation,
            lap_callback=self.update_lap
        )

        self.tabs.addTab(self.simulation_tab, "Run Simulation")
        self.tabs.addTab(self.optimization_tab, "Optimize Simulation")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setWindowTitle("Simulation MVP")
        self.resize(1200, 600)

    def run_simulation(self):
        self.simulation_tab.start_button.setEnabled(False)
        self.simulation_tab.sim_output_text.clear()

        self.simulation_thread = SimulationThread(self.simulation_settings, None)
        self.simulation_thread.update_signal.connect(self.simulation_tab.sim_output_text.append)
        self.simulation_thread.plot_data_signal.connect(self.simulation_tab.sim_canvas.plot_simulation_results)
        self.simulation_thread.finished.connect(lambda: self.simulation_tab.start_button.setEnabled(True))

        if self.optimization_thread is not None:
            self.optimization_thread.model_signal.connect(self.optimization_tab.speed_canvas.plot_optimized_speeds)

        self.simulation_thread.start()

    def update_sim_plot(self, results_dict):
        """
        This method passes a dictionary of time series results to the SimulationCanvas,
        which renders them as a grid of plots.

        :param results_dict: Dictionary mapping metric labels to (timestamps, values) tuples.
        :type results_dict: dict
        :returns: None
        :rtype: None
        """
        self.simulation_tab.sim_canvas.plot_simulation_results(results_dict)
    def update_speed_plot(self, model):
        """
        This method visualizes the optimized lap speeds on a folium map by passing
        the model to the FoliumMapWidget.

        :param model: The optimized simulation model containing GIS and speed data.
        :type model: object
        :returns: None
        :rtype: None
        """
        self.optimization_tab.speed_canvas.plot_optimized_speeds(model)

    def optimize_simulation(self):
        self.optimization_tab.optimize_button.setEnabled(False)
        self.optimization_tab.output_text.clear()

        self.optimization_thread = OptimizationThread(self.simulation_settings)
        self.optimization_thread.update_signal.connect(self.optimization_tab.output_text.append)
        self.optimization_thread.progress_signal.connect(
            lambda value: self.optimization_tab.progress_bar.setValue(value))
        self.optimization_thread.model_signal.connect(self.optimization_tab.speed_canvas.plot_optimized_speeds)
        self.optimization_thread.finished.connect(lambda: self.optimization_tab.optimize_button.setEnabled(True))

        self.optimization_thread.start()

    def update_output(self, message):
        self.output_text.append(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulationApp()
    window.show()
    sys.exit(app.exec_())
import random
import string
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QProgressBar, QTabWidget, \
    QLabel, QSizePolicy
from PyQt6.QtCore import QThread, pyqtSignal, QSize

from simulation.cmd import run_simulation
from simulation.cmd.run_simulation import SimulationSettings, build_model
from simulation.config import speeds_directory
from simulation.optimization.genetic import GeneticOptimization, OptimizationSettings
from simulation.utils import InputBounds
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from collections import OrderedDict
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
        self.toolbar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)  # Prevent expanding into plots
        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)  # Add margins for proper spacing
        self.setLayout(layout)

    def plot_simulation_results(self, results_dict):
        """Updates the plots with multiple simulation data series, ensuring good formatting."""
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


class SpeedCanvas(FigureCanvas):
    """Canvas to display optimized speeds dynamically with color bar and lap navigation buttons."""

    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.cax = self.fig.add_axes([0.92, 0.1, 0.03, 0.8])  # Color bar axis
        super().__init__(self.fig)
        self.setParent(parent)

        self.lap_num = 0  # Track the current lap
        self.model = None  # Store the model for lap switching
        self.norm = plt.Normalize(0, 80)  # Normalize for color mapping
        self.cmap = plt.get_cmap('jet')  # Use Jet colormap for better contrast

    def plot_optimized_speeds(self, model):
        """Plot the optimized speeds for the given model and store it for navigation."""
        self.model = model  # Store the model so we can switch laps
        self.update_plot()

    def update_plot(self):
        """Update the plot for the selected lap."""
        if self.model is None:
            return

        num_coordinates = int(self.model.gis.num_unique_coords)
        gis_indices, speed_kmh = self.model.get_results(["closest_gis_indices", "speed_kmh"])
        coords = self.model.gis.get_path()

        self.ax.clear()
        self.ax.set_title(f"Optimized Speeds - Lap {self.lap_num}")

        gis_index_mean_speeds, relevant_coords = self.calculate_coords(
            self.lap_num, coords, num_coordinates, gis_indices, speed_kmh
        )

        # Plot speed heatmap
        lines = []
        for j, (start, stop) in enumerate(zip(relevant_coords[:-1], relevant_coords[1:])):
            y, x = zip(start, stop)
            line, = self.ax.plot(x, y, color=self.cmap(self.norm(gis_index_mean_speeds[j])), linewidth=4.0)
            lines.append(line)

        # Attach hover cursor to display speed at each point
        cursor = mplcursors.cursor(lines, hover=True)

        @cursor.connect("add")
        def on_add(sel):
            index = lines.index(sel.artist)
            sel.annotation.set(text=f"Speed: {gis_index_mean_speeds[index]:.1f} km/h", fontsize=10,
                               bbox=dict(facecolor='white', alpha=0.8))

        # Update color bar dynamically
        self.cax.clear()
        sm = cm.ScalarMappable(cmap=self.cmap, norm=self.norm)
        sm.set_array([])
        self.fig.colorbar(sm, cax=self.cax, label="Speed (km/h)")

        self.draw()

    def update_lap(self, direction):
        """Change lap number based on button press."""
        if direction == "next":
            self.lap_num += 1
        elif direction == "prev":
            self.lap_num = max(0, self.lap_num - 1)  # Prevent negative laps
        self.update_plot()

    def calculate_coords(self, lap_num, coords, num_coordinates, gis_indices, speed_kmh):
        """Calculate the mean speed at each coordinate for a given lap."""
        beginning_coordinate = num_coordinates * lap_num
        end_coordinate = num_coordinates * (lap_num + 1)
        coords_of_interest = coords[beginning_coordinate:end_coordinate + 1]

        gis_index_mean_speeds = OrderedDict()

        for i in range(len(coords_of_interest)):
            lap_offset = num_coordinates * lap_num
            k = i + lap_offset
            j = k
            while True:
                indices = np.where(gis_indices == k)[0]
                try:
                    begin, end = indices[0], indices[-1] + 1
                except IndexError:
                    gis_index_mean_speeds[k - lap_offset] = -1
                    k += 1
                    continue

                for index in range(j, k + 1):
                    gis_index_mean_speeds[index - lap_offset] = np.mean(speed_kmh[begin:end])
                break

        return gis_index_mean_speeds, coords_of_interest


class SimulationThread(QThread):
    update_signal = pyqtSignal(str)
    plot_data_signal = pyqtSignal(dict)  # Send multiple plots as a dictionary

    def __init__(self, settings, speeds_filename):
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

    def __init__(self, settings):
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
            # optimization_settings.generation_limit = 2  # For testing purposes

            genetic_optimization = GeneticOptimization(
                simulation_model, bounds, settings=optimization_settings, pbar=None,
                progress_signal=self.progress_signal, update_signal=self.update_signal  # Attach signals
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


class SimulationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.optimization_thread = None

    def initUI(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simulation_tab = QWidget()
        self.optimization_tab = QWidget()

        self.tabs.addTab(self.simulation_tab, "Run Simulation")
        self.tabs.addTab(self.optimization_tab, "Optimize Simulation")

        self.init_simulation_tab()
        self.init_optimization_tab()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.setWindowTitle("Simulation MVP")
        self.resize(1600, 1200)  # Adjusted for better layout

    def init_simulation_tab(self):
        layout = QVBoxLayout()

        self.start_button = QPushButton("Run Simulation")
        self.start_button.clicked.connect(self.run_simulation)
        layout.addWidget(self.start_button)

        self.sim_output_text = QTextEdit()
        self.sim_output_text.setReadOnly(True)
        self.sim_output_text.setFixedHeight(100)  # Set a fixed height

        layout.addWidget(self.sim_output_text)

        # Add the Matplotlib canvas inside the simulation tab
        self.sim_canvas = SimulationCanvas()
        layout.addWidget(self.sim_canvas)

        self.simulation_tab.setLayout(layout)

    def init_optimization_tab(self):
        layout = QVBoxLayout()

        self.optimize_button = QPushButton("Optimize Simulation")
        self.optimize_button.clicked.connect(self.optimize_simulation)
        layout.addWidget(self.optimize_button)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Add SpeedCanvas (optimized speeds plot)
        self.speed_canvas = SpeedCanvas(self)
        layout.addWidget(self.speed_canvas)

        # Add Lap Navigation Buttons
        self.prev_lap_button = QPushButton("Previous Lap")
        self.prev_lap_button.clicked.connect(lambda: self.speed_canvas.update_lap("prev"))

        self.next_lap_button = QPushButton("Next Lap")
        self.next_lap_button.clicked.connect(lambda: self.speed_canvas.update_lap("next"))

        nav_layout = QVBoxLayout()
        nav_layout.addWidget(self.prev_lap_button)
        nav_layout.addWidget(self.next_lap_button)

        layout.addLayout(nav_layout)  # Add navigation buttons below plot

        self.optimization_tab.setLayout(layout)

    def run_simulation(self):
        self.start_button.setEnabled(False)
        self.sim_output_text.clear()

        settings = SimulationSettings(race_type="FSGP", verbose=True, granularity=1)
        speeds_filename = None

        self.simulation_thread = SimulationThread(settings, speeds_filename)
        self.simulation_thread.update_signal.connect(self.sim_output_text.append)
        self.simulation_thread.plot_data_signal.connect(self.update_sim_plot)  # Connect to update live plot
        self.simulation_thread.finished.connect(lambda: self.start_button.setEnabled(True))
        if self.optimization_thread is not None:
            self.optimization_thread.model_signal.connect(self.update_speed_plot)  # Connect speed update
        self.simulation_thread.start()

    def update_sim_plot(self, results_dict):
        """Update the Matplotlib canvas with new simulation data."""
        self.sim_canvas.plot_simulation_results(results_dict)

    def update_speed_plot(self, model):
        """Update the SpeedCanvas with the optimized model."""
        self.speed_canvas.plot_optimized_speeds(model)

    def optimize_simulation(self):
        self.optimize_button.setEnabled(False)
        self.output_text.clear()

        settings = SimulationSettings(race_type="FSGP", verbose=True, granularity=1)
        self.optimization_thread = OptimizationThread(settings)
        self.optimization_thread.update_signal.connect(self.update_output)
        self.optimization_thread.progress_signal.connect(lambda value: self.progress_bar.setValue(value))
        self.optimization_thread.model_signal.connect(self.update_speed_plot)
        self.optimization_thread.finished.connect(lambda: self.optimize_button.setEnabled(True))
        self.optimization_thread.start()

    def update_output(self, message):
        self.output_text.append(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulationApp()
    window.show()
    sys.exit(app.exec())

import random
import string
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal
from simulation.cmd.run_simulation import run_simulation
from simulation.config import SimulationHyperparametersConfig, InitialConditions, CarConfig, EnvironmentConfig
from simulation.utils import InputBounds
from simulation.optimization.genetic import DifferentialEvolutionOptimization
import numpy as np
from pathlib import Path
from simulation.model.ModelBuilder import ModelBuilder
from prescriptive_interface import SimulationSettingsDict

config_dir = Path(__file__).parent.parent / "simulation" / "config"
my_speeds_dir = Path("prescriptive_interface/speeds_directory")
my_speeds_dir.mkdir(parents=True, exist_ok=True)  # Create it if it doesn't exist


class SimulationThread(QThread):
    update_signal = pyqtSignal(str)
    plot_data_signal = pyqtSignal(dict)  # Send multiple plots as a dictionary

    def __init__(self, settings: SimulationSettingsDict, speeds_filename: Optional[str],
                 optimized_speeds: Optional[np.ndarray] = None):
        super().__init__()
        self.settings = settings
        self.speeds_filename = speeds_filename
        self.optimized_speeds = optimized_speeds

    def run(self):
        self.update_signal.emit("Starting simulation...")

        try:
            # Determine speeds_directory array
            if self.optimized_speeds is not None:
                speeds = self.optimized_speeds
            elif self.speeds_filename is not None:
                speeds = np.load(my_speeds_dir / (self.speeds_filename + ".npy"))
            else:
                dummy_model = run_simulation(
                    competition_name=self.settings["race_type"],
                    plot_results=False,
                    verbose=self.settings["verbose"],
                    speed_dt=self.settings["granularity"],
                    car=self.settings["car"]
                )
                driving_hours = dummy_model.get_driving_time_divisions()
                speeds = np.array([45] * driving_hours)

            # Run simulation with updated API
            simulation_model = run_simulation(
                competition_name=self.settings["race_type"],
                plot_results=False,
                verbose=self.settings["verbose"],
                speed_dt=self.settings["granularity"],
                car=self.settings["car"],
                speeds=speeds
            )

            # Extract multiple data series
            results_keys = ["timestamps", "speed_kmh", "distances", "state_of_charge",
                            "delta_energy", "solar_irradiances",
                            "wind_speeds"]  # !!! changed to get rid of bottom 3 things
            results_values = simulation_model.get_results(results_keys)
            results_dict = {key: (results_values[0], values) for key, values in
                            zip(results_keys[1:], results_values[1:])}

            self.plot_data_signal.emit(results_dict)

            # Format result summary
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
    model_signal = pyqtSignal(object, object, int)  # Emits optimized simulation model, speeds

    def __init__(self, settings: SimulationSettingsDict,
                 popsize: int,
                 maxiter: int,
                 initial_conditions: InitialConditions,
                 hyperparameters: SimulationHyperparametersConfig,
                 environment_config: EnvironmentConfig,
                 car_config: CarConfig,
                 get_weather: bool
                 ):
        super().__init__()
        self.settings = settings
        self.popsize = popsize
        self.maxiter = maxiter
        self.hyperparameters = hyperparameters
        self.initial_conditions = initial_conditions
        self.environment_config = environment_config
        self.car_config = car_config
        self.get_weather = get_weather

    def run(self):
        self.update_signal.emit("Starting optimization...")

        try:
            simulation_builder = (
                ModelBuilder()
                .set_environment_config(
                    self.environment_config,
                    rebuild_weather_cache=self.get_weather,
                    rebuild_route_cache=False,
                    rebuild_competition_cache=False,
                )
                .set_hyperparameters(self.hyperparameters)
                .set_initial_conditions(self.initial_conditions)
                .set_car_config(self.car_config)
            )
            simulation_builder.compile()

            base_model = simulation_builder.get()

            driving_laps = base_model.num_laps

            # Bounds
            maximum_speed = 60
            minimum_speed = 0

            bounds = InputBounds()
            bounds.add_bounds(driving_laps, minimum_speed, maximum_speed)

            # Initial guess
            input_speed = np.array([60] * driving_laps)
            base_model.run_model(
                speed=input_speed,
                plot_results=False,
                verbose=self.settings["verbose"],
                route_visualization=False
            )

            genetic_optimization = DifferentialEvolutionOptimization(base_model, bounds, maxiter=self.maxiter,
                                                                     popsize=self.popsize)
            optimized_speed_array = genetic_optimization.maximize(progress_signal=self.progress_signal)
            laps_per_index = int(
                driving_laps / genetic_optimization.num_genes)  # Each speed in the above array is used for this many laps

            self.progress_signal.emit(100)

            # Rerun simulation with optimized speeds_directory
            optimized_model = run_simulation(
                competition_name=self.settings["race_type"],
                plot_results=False,
                verbose=self.settings["verbose"],
                speed_dt=self.settings["granularity"],
                car=self.settings["car"],
                speeds=optimized_speed_array
            )

            filename = self.get_random_string(7) + ".npy"
            np.save(my_speeds_dir / filename, optimized_speed_array)
            self.update_signal.emit(f"Optimization completed successfully! Results saved in: {filename}")
            self.model_signal.emit(optimized_model, optimized_speed_array, laps_per_index)

        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")

    def get_random_string(self, length: int) -> str:
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

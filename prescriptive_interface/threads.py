import random
import string
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal
from simulation.cmd.run_simulation import run_simulation
from simulation.config import SimulationHyperparametersConfig, InitialConditions, CarConfig, EnvironmentConfig
from simulation.model import Model
from simulation.utils import InputBounds
from simulation.optimization.genetic import DifferentialEvolutionOptimization
import numpy as np
from pathlib import Path
from simulation.model.ModelBuilder import ModelBuilder
from prescriptive_interface import SimulationSettingsDict
import traceback
import math


config_dir = Path(__file__).parent.parent / "simulation" / "config"
my_speeds_dir = Path("prescriptive_interface/speeds_directory")
my_speeds_dir.mkdir(parents=True, exist_ok=True)  # Create it if it doesn't exist


class SimulationThread(QThread):
    update_signal = pyqtSignal(str)
    plot_data_signal = pyqtSignal(dict)  # Send multiple plots as a dictionary

    def __init__(self, settings: SimulationSettingsDict, model: Model = None, speeds_filename: Optional[str] = None,
                 optimized_speeds: Optional[np.ndarray] = None):
        super().__init__()
        self.settings = settings
        self.speeds_filename = speeds_filename
        self.optimized_speeds = optimized_speeds
        self.model = model

    def run(self):
        self.update_signal.emit("Starting simulation...")

        try:
            if self.model is None:
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

            else:
                simulation_model = self.model

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
            speeds = results[3]
            formatted_results = (
                f"Distanced Travelled: {results[2]:.2f}km\n"
                f"Average Driving Speed: {np.average(speeds[speeds > 0.5]):.2f}km/h\n"
                f"Final SOC: {results[4]:.2f}%\n"
            )
            self.update_signal.emit(formatted_results)

        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")


class OptimizationThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    model_signal = pyqtSignal(object, object, int, int)  # Emits optimized simulation model, speeds

    def __init__(self, settings: SimulationSettingsDict,
                 popsize: int,
                 maxiter: int,
                 initial_conditions: InitialConditions,
                 hyperparameters: SimulationHyperparametersConfig,
                 environment_config: EnvironmentConfig,
                 car_config: CarConfig,
                 get_weather: bool,
                 days: list[str]
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
        self.days = days

    def run(self):
        self.update_signal.emit("Starting optimization...")

        try:
            for day in self.days:
                for range_name, time_range in self.environment_config.competition_config.time_ranges.items():
                    if day in time_range.keys():
                        del self.environment_config.competition_config.time_ranges[range_name][day]

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

            # Rerun simulation with optimized speeds
            base_model.run_model(
                speed=optimized_speed_array,
                plot_results=False,
                verbose=self.settings["verbose"],
                route_visualization=False
            )

            num_laps_completed = math.floor(base_model.get_results("distance_travelled") * 1000 / base_model.gis.path_length)

            filename = self.get_random_string(7) + ".npy"
            np.save(my_speeds_dir / filename, optimized_speed_array)
            self.update_signal.emit(f"Optimization completed successfully! Results saved in: {filename}")
            self.model_signal.emit(base_model, optimized_speed_array, laps_per_index, num_laps_completed)

        except Exception:
            self.update_signal.emit(traceback.format_exc())

    def get_random_string(self, length: int) -> str:
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

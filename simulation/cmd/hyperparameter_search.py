import sys
import csv
import numpy as np

from simulation.model.Model import Model
from simulation.utils.InputBounds import InputBounds
from simulation.optimization.genetic import GeneticOptimization
from simulation.data.results import results_directory
from simulation.data.assemble import Assembler
from simulation.cmd.run_simulation import build_model, get_default_settings
from simulation.config import SimulationHyperparametersConfig, SimulationReturnType
from tqdm import tqdm


def main(competition_name: str, car_name: str, speed_dt: int):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param speed_dt:
    :param car_name:
    :param competition_name:
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """
    initial_conditions, environment, car_config = get_default_settings(
        competition_name, car_name
    )

    hyperparameters = SimulationHyperparametersConfig.build_from(
        {
            "simulation_period": 10,
            "return_type": SimulationReturnType.distance_and_time,
            "speed_dt": speed_dt,
        }
    )
    simulation_model = build_model(
        environment, hyperparameters, initial_conditions, car_config
    )

    # Initialize a "guess" speed array
    driving_hours = simulation_model.get_driving_time_divisions()

    # Set up optimization models
    maximum_speed = 60
    minimum_speed = 0

    bounds = InputBounds()
    bounds.add_bounds(driving_hours, minimum_speed, maximum_speed)

    driving_hours = simulation_model.get_driving_time_divisions()
    input_speed = np.array([60] * driving_hours)

    # Run simulation model with the "guess" speed array
    simulation_model.run_model(speed=input_speed, plot_results=False, verbose=False)

    run_hyperparameter_search(simulation_model, bounds)


def run_hyperparameter_search(simulation_model: Model, bounds: InputBounds):
    evals_per_setting: int = 3
    settings_file = results_directory / "settings.csv"
    stop_index = 0

    with open(settings_file, "r") as f:
        csv_reader = csv.reader(f, delimiter=",")
        settings_list = GeneticOptimization.parse_csv_into_settings(csv_reader)

    total_num = (
        GeneticOptimization.get_total_generations(settings_list) * evals_per_setting
    )
    assembler = Assembler(results_directory)
    with tqdm(
        total=total_num,
        file=sys.stdout,
        desc="Running hyperparameter search",
        position=0,
        leave=True,
    ) as pbar:
        try:
            for settings in settings_list:
                stop_index += 1
                for x in range(evals_per_setting):
                    geneticOptimization = GeneticOptimization(
                        simulation_model,
                        bounds,
                        settings=settings,
                        pbar=pbar,
                        plot_fitness=True,
                    )
                    geneticOptimization.maximize()
                    evolution = assembler.marshal_evolution(
                        geneticOptimization, simulation_model
                    )
                    assembler.write_evolution(evolution)

        except KeyboardInterrupt:
            print(
                f"Finished {stop_index - 1} setting(s), stopped while evaluating setting {stop_index}."
            )
            exit()
    print("Hyperparameter search has concluded.")

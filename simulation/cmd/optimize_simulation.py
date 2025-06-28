import argparse

import numpy as np
import sys
import random
import string

from simulation.utils.InputBounds import InputBounds
from simulation.config import speeds_directory
from simulation.optimization.genetic import OptimizationSettings, DifferentialEvolutionOptimization
from simulation.cmd.run_simulation import build_model, get_default_settings
from simulation.config import SimulationHyperparametersConfig, SimulationReturnType
from tqdm import tqdm


def main(competition_name: str, car_name: str, speed_dt: int):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Genetic optimization, and save the results.

    :param speed_dt:
    :param car_name:
    :param competition_name:
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    # Build simulation model
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

    # Initialize a "guess" speed array
    driving_laps = environment.competition_config.tiling

    # Set up optimization models
    maximum_speed = 60
    minimum_speed = 0

    bounds = InputBounds()
    bounds.add_bounds(driving_laps, minimum_speed, maximum_speed)

    # Perform optimization with Genetic Optimization
    optimization_settings: OptimizationSettings = OptimizationSettings()
    with tqdm(
        total=optimization_settings.generation_limit,
        file=sys.stdout,
        desc="Optimizing driving speeds",
        position=0,
        leave=True,
        unit="Generation",
        smoothing=1.0,
    ) as pbar:
        initial_population = None

        while True:
            print(f"Optimizing for {driving_laps} laps!")
            environment.competition_config.tiling = driving_laps

            simulation_model = build_model(
                environment, hyperparameters, initial_conditions, car_config
            )

            genetic_optimization = DifferentialEvolutionOptimization(
                simulation_model, bounds, pbar, popsize=6
            )

            try:
                results_genetic = genetic_optimization.maximize(initial_population, pbar)
                break

            except ValueError:
                initial_population = genetic_optimization.bestinput
                driving_laps += 20

    simulation_model.run_model(results_genetic, plot_results=True)

    filename = get_random_string(7) + ".npy"
    np.save(speeds_directory / filename, results_genetic)
    print(f"Saved optimized results in: {filename}\n")


def get_random_string(length: int) -> str:
    characters = string.ascii_letters + string.digits
    random_string = "".join(random.choice(characters) for _ in range(length))

    return random_string


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--race_type",
        required=False,
        default="FSGP",
        help="Define which race should be simulated. (ASC/FSGP)",
        type=str,
    )

    parser.add_argument(
        "--car",
        required=False,
        default="Brightside",
        type=str,
        help="Name of car model",
    )

    parser.add_argument(
        "--granularity",
        required=False,
        default=60,
        help="Define how granular the speed array should "
        "be, where 1 is hourly and 2 is bi-hourly.",
        type=int,
    )

    args = parser.parse_args()

    main(competition_name=args.race_type,
         car_name = args.car,
         speed_dt= args.granularity)
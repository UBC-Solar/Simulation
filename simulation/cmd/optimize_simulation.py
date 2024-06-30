import argparse

import numpy as np
import sys
import random
import string

from simulation.utils.InputBounds import InputBounds
from simulation.config import speeds_directory
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.optimization.genetic import GeneticOptimization, OptimizationSettings
from simulation.cmd.run_simulation import SimulationSettings, get_default_settings
from simulation.common.race import Race
from tqdm import tqdm


def main(settings):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Genetic optimization, and save the results.

    :param SimulationSettings settings: object that stores settings for the simulation and optimization sequence
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    # Build simulation model
    initial_conditions, model_parameters = get_default_settings(Race.RaceType(settings.race_type))
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.RaceType(settings.race_type)) \
        .set_return_type(settings.return_type) \
        .set_granularity(settings.granularity)

    simulation_model = simulation_builder.get()

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
    simulation_model.run_model(speed=input_speed, plot_results=False,
                               verbose=settings.verbose,
                               route_visualization=settings.route_visualization)

    # Perform optimization with Genetic Optimization
    optimization_settings: OptimizationSettings = OptimizationSettings()
    with tqdm(total=optimization_settings.generation_limit, file=sys.stdout, desc="Optimizing driving speeds",
              position=0, leave=True, unit="Generation", smoothing=1.0) as pbar:
        geneticOptimization = GeneticOptimization(simulation_model, bounds, settings=optimization_settings, pbar=pbar)
        results_genetic = geneticOptimization.maximize()

    simulation_model.run_model(results_genetic, plot_results=True)

    filename = get_random_string(7) + ".npy"
    np.save(speeds_directory / filename, results_genetic)
    print(f"Saved optimized results in: {filename}.npy\n")


def get_random_string(length: int) -> str:
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))

    return random_string


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_type", required=False, default="FSGP", help="Define which race should be simulated. ("
                                                                            "ASC/FSGP)", type=str)
    parser.add_argument("--granularity", required=False, default=60, help="Define how granular the speed array should "
                                                                          "be, where 1 is hourly and 2 is bi-hourly.",
                        type=int)

    args = parser.parse_args()

    main(SimulationSettings(race_type=args.race_type, verbose=False, granularity=args.granularity))

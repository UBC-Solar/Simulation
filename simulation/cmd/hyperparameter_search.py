import sys
import csv
import numpy as np

from simulation.model.Simulation import Simulation, SimulationReturnType
from simulation.utils.InputBounds import InputBounds
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.optimization.genetic import GeneticOptimization
from simulation.cmd.run_simulation import SimulationSettings, get_default_settings
from simulation.data.results import results_directory
from simulation.data.assemble import Assembler
from simulation.common.race import Race
from tqdm import tqdm
import argparse


"""
Description: Execute simulation optimization sequence. 
"""


def main(settings):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param SimulationSettings settings: object that stores settings for the simulation and optimization sequence
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    # Build simulation model
    initial_conditions, model_parameters = get_default_settings(Race.RaceType(settings.race_type))
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.RaceType(settings.race_type)) \
        .set_return_type(SimulationReturnType.distance_and_time) \
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


    run_hyperparameter_search(simulation_model, bounds)


def run_hyperparameter_search(simulation_model: Simulation, bounds: InputBounds):
    evals_per_setting: int = 3
    settings_file = results_directory / "settings.csv"
    stop_index = 0

    with open(settings_file, 'r') as f:
        csv_reader = csv.reader(f, delimiter=',')
        settings_list = GeneticOptimization.parse_csv_into_settings(csv_reader)

    total_num = GeneticOptimization.get_total_generations(settings_list) * evals_per_setting
    assembler = Assembler(results_directory)
    with tqdm(total=total_num, file=sys.stdout, desc="Running hyperparameter search", position=0, leave=True) as pbar:
        try:
            for settings in settings_list:
                stop_index += 1
                for x in range(evals_per_setting):
                    geneticOptimization = GeneticOptimization(simulation_model, bounds, settings=settings, pbar=pbar,
                                                              plot_fitness=True)
                    geneticOptimization.maximize()
                    evolution = assembler.marshal_evolution(geneticOptimization, simulation_model)
                    assembler.write_evolution(evolution)

        except KeyboardInterrupt:
            print(f"Finished {stop_index - 1} setting(s), stopped while evaluating setting {stop_index}.")
            exit()
    print("Hyperparameter search has concluded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_type", required=False, default="FSGP", help="Define which race should be simulated. ("
                                                                            "ASC/FSGP)", type=str)
    parser.add_argument("--granularity", required=False, default=1, help="Define how granular the speed array should "
                                                                         "be, where 1 is hourly and 2 is bi-hourly.",
                        type=int)

    args = parser.parse_args()

    main(SimulationSettings(race_type=args.race_type, verbose=False, granularity=args.granularity))

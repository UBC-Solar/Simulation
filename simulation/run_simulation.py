import datetime

import numpy as np
import json
import sys
from main.Simulation import Simulation, SimulationReturnType
from optimization.bayesian import BayesianOptimization
from optimization.random_opt import RandomOptimization
from utils.InputBounds import InputBounds
from config import config_directory
from utils.SimulationBuilder import SimulationBuilder

"""
Description: Execute simulation optimization sequence. 
"""


class SimulationSettings:
    """

    This class stores settings that will be used by the simulation.

    """

    def __init__(self, race_type="ASC", golang=True, return_type=SimulationReturnType.distance_travelled,
                 optimization_iterations=20, route_visualization=False, verbose=False, granularity=1):
        self.race_type = race_type
        self.optimization_iterations = optimization_iterations
        self.golang = golang
        self.return_type = return_type
        self.route_visualization = route_visualization
        self.verbose = verbose
        self.granularity = granularity

    def __str__(self):
        return (f"GoLang is {str('enabled.' if self.golang else 'disabled.')}\n"
                f"Verbose is {str('on.' if self.verbose else 'off.')}\n"
                f"Route visualization is {str('on.' if self.route_visualization else 'off.')}\n"
                f"Optimizing for {str('time.' if self.return_type == 0 else 'distance.')}\n"
                f"Will perform {self.optimization_iterations} optimization iterations.\n")


def main():
    """

    This is the entry point to Simulation.
    First, parse command line arguments, then execute simulation optimization sequence.

    """

    #  ----- Parse commands passed from command line ----- #

    cmds = sys.argv
    simulation_settings = parse_commands(cmds)

    print(str(simulation_settings))

    #  ----- Run simulation ----- #

    run_simulation(simulation_settings)

    print("Simulation has completed.")


def run_simulation(settings):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param SimulationSettings settings: object that stores settings for the simulation and optimization sequence
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    # Build simulation model
    initial_conditions, model_parameters = get_default_settings(settings.race_type)
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, settings.race_type) \
        .set_golang(settings.golang) \
        .set_return_type(settings.return_type) \
        .set_granularity(settings.granularity)

    simulation_model = simulation_builder.get()

    # Initialize a "guess" speed array
    driving_hours = simulation_model.get_driving_time_divisions()
    input_speed = np.array([30] * driving_hours)

    # Run simulation model with the "guess" speed array
    unoptimized_time = simulation_model.run_model(speed=input_speed, plot_results=True,
                                                  verbose=settings.verbose,
                                                  route_visualization=settings.route_visualization)

    # Set up optimization models
    maximum_speed = 60
    minimum_speed = 0

    bounds = InputBounds()
    bounds.add_bounds(driving_hours, minimum_speed, maximum_speed)

    # Initialize optimization methods
    optimization = BayesianOptimization(bounds, simulation_model.run_model)
    random_optimization = RandomOptimization(bounds, simulation_model.run_model)

    # Perform optimization with Bayesian Optimization
    results = optimization.maximize(init_points=5, n_iter=settings.optimization_iterations, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=settings.verbose,
                                           route_visualization=settings.route_visualization)

    # Perform optimization with random optimization
    results_random = random_optimization.maximize(iterations=settings.optimization_iterations)
    optimized_random = simulation_model.run_model(speed=np.fromiter(results_random, dtype=float), plot_results=True,
                                                  verbose=settings.verbose,
                                                  route_visualization=settings.route_visualization)

    #  ----- Output results ----- #

    display_output(settings.return_type, unoptimized_time, optimized, optimized_random, results,
                   results_random)

    return unoptimized_time


def display_output(return_type, unoptimized, optimized, optimized_random, results, results_random):
    if return_type is SimulationReturnType.time_taken:
        print(
            f'TimeSimulation results. Time Taken: {-1 * unoptimized} seconds, '
            f'({str(datetime.timedelta(seconds=int(-1 * unoptimized)))})')
        print(
            f'Optimized results. Time taken: {-1 * optimized} seconds, '
            f'({str(datetime.timedelta(seconds=int(-1 * optimized)))})')
        print(
            f'Random results. Time taken: {-1 * optimized_random} seconds, '
            f'({str(datetime.timedelta(seconds=int(-1 * optimized_random)))})')

    elif return_type is SimulationReturnType.distance_travelled:
        print(f'Distance travelled: {unoptimized}')
        print(f'Optimized results. Max traversable distance: {optimized}')
        print(f'Random results. Max traversable distance: {optimized_random}')

    print(f'Optimized Speeds array: {results}')
    print(f'Random Speeds array: {results_random}')

    return unoptimized


def display_commands():
    """

    Display all valid command line arguments to the user.

    """

    print("------------------------COMMANDS-----------------------\n"
          "-help                 Display list of valid commands.\n"
          "\n"
          "-race_type            Define which race should be simulated. \n"
          "                      (ASC/FSGP)\n"
          "\n"
          "-golang               Define whether golang implementations\n"
          "                      will be used. \n"
          "                      (True/False)\n"
          "\n"
          "-optimize             Define what data the simulation\n"
          "                      should optimize. \n"
          "                      (time_taken/distance_travelled)\n"
          "\n"
          "-iter                 Set how many iterations of optimizations\n"
          "                      should be performed on the simulation.\n"
          "\n"
          "-verbose              Set whether simulation methods should\n"
          "                      execute as verbose.\n"
          "                      (True/False)\n"
          "\n"
          "-route_visualization   Define whether the simulation route\n"
          "                      should be plotted and visualized.\n"
          "                      (True/False)\n"
          "\n"
          "-granularity          Define how granular the speed array\n"
          "                      should be, where 1 is hourly and 2 is\n"
          "                      bi-hourly.\n"
          "\n"
          "-------------------------USAGE--------------------------\n"
          ">>>python3 run_simulation.py -golang=False -optimize=time_taken -iter=3\n")


def parse_commands(cmds) -> SimulationSettings:
    """

    Parse commands from command line into parameters for the simulation.

    :param cmds: list of commands from to be parsed into parameters.
    :return: return a SimulationParameters object of defaulted or parsed parameters.
    :rtype: SimulationSettings

    """

    simulation_settings = SimulationSettings()

    command_to_action = {
        '-golang': lambda x: set_golang(x),
        '-optimize': lambda x: set_return_type(x),
        '-iter': lambda x: set_iterations(x),
        '-verbose': lambda x: set_verbose(x),
        '-route_visualization': lambda x: set_route_visualization(x),
        '-race_type': lambda x: set_race_type(x),
        '-granularity': lambda x: set_granularity(x)
    }

    def set_golang(value: str):
        simulation_settings.golang = True if value == 'True' or value == 'true' else False

    def set_return_type(value: str):
        try:
            simulation_settings.return_type = SimulationReturnType(value)
        except ValueError:
            raise ValueError(f"{value} could not be recognized as a SimulationReturnType!")

    def set_iterations(value: str):
        simulation_settings.optimization_iterations = int(value)

    def set_verbose(value: str):
        simulation_settings.verbose = True if value == 'True' or value == 'true' else False

    def set_route_visualization(value: str):
        simulation_settings.route_visualization = True if value == 'True' or value == 'true' else False

    def set_race_type(value: str):
        assert value in ['ASC', 'FSGP'], f"Invalid race type {value}. Please enter 'ASC' or 'FSGP'."
        simulation_settings.race_type = value

    def set_granularity(value: float):
        simulation_settings.granularity = value

    # If the user has requested '-help', display list of valid commands.
    if "-help" in cmds:
        display_commands()
        exit()

    # Loop through commands and parse them to assign their values to their respective parameters.
    for cmd in cmds:
        if not cmd[0] == '-':
            continue

        split_cmd = cmd.split('=')

        try:
            action = command_to_action[split_cmd[0]]
            action(split_cmd[1])
        except KeyError:
            raise KeyError(f"{cmd} not identified!")

    return simulation_settings


def run_unoptimized_and_export(input_speed=None, values=None, race_type="ASC", granularity=1, golang=True):
    """

    Export simulation data.

    :param input_speed: defaulted to 30km/h, an array of speeds that the Simulation will use.
    :param values: defaulted to what was outputted by now-deprecated SimulationResults object, a tuple of strings that
    each correspond to a value or array that the Simulation will export. See Simulation.get_results() for valid keys.
    :param race_type: define the race type, either "ASC" or "FSGP"
    :param granularity: define the granularity of Simulation speed array
    :param golang: define whether GoLang
    implementations should be used.
    :param granularity: control how granular the time divisions of Simulation should be
    :param race_type: whether the race is ASC or FSGP

    """

    # Get a basic simulation model
    simulation_model = build_basic_model(race_type, golang, granularity)

    driving_hours = simulation_model.get_driving_time_divisions()
    if input_speed is None:
        input_speed = np.array([30] * driving_hours)
    if values is None:
        values = "default"

    simulation_model.run_model(speed=input_speed, plot_results=True, verbose=False, route_visualization=False,
                               plot_portion=(0.0 / 8.0, 8.0 / 8.0))
    results_array = simulation_model.get_results(values)

    return results_array


def get_default_settings(race_type: str = "ASC") -> tuple[dict, dict]:
    #  ----- Load initial conditions -----
    with open(config_directory / f"initial_conditions_{race_type}.json") as f:
        initial_conditions = json.load(f)

    #  ----- Load model parameters -----
    config_path = config_directory / f"settings_{race_type}.json"
    with open(config_path) as f:
        model_parameters = json.load(f)

    return initial_conditions, model_parameters


def build_basic_model(race_type: str = "ASC", golang: bool = True, granularity: float = 1) -> Simulation:
    initial_conditions, model_parameters = get_default_settings(race_type)
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, race_type) \
        .set_golang(golang) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(granularity)
    return simulation_builder.get()


if __name__ == "__main__":
    main()

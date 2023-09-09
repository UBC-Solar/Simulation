import datetime

import numpy as np
import json
import sys

from main.Simulation import SimulationReturnType
from optimization.bayesian import BayesianOptimization
from optimization.random import RandomOptimization
from utils.InputBounds import InputBounds
from config import config_directory
from common.simulationBuilder import SimulationBuilder

"""
Description: Execute simulation optimization sequence. 
"""


class SimulationSettings:
    """

    This class stores settings that will be used by the simulation.

    """
    def __init__(self, race_type="ASC", golang=True, return_type=SimulationReturnType.time_taken, optimization_iterations=5, route_visualization=False, verbose=False, granularity=1):
        self.race_type = race_type
        self.optimization_iterations = optimization_iterations
        self.golang = golang
        self.return_type = return_type
        self.route_visualization = route_visualization
        self.verbose = verbose
        self.granularity = granularity


def run_simulation(settings):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param SimulationSettings settings: object that stores settings for the simulation and optimization sequence
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    #  ----- Load initial conditions ----- #

    with open(config_directory / "initial_conditions.json") as f:
        initial_conditions = json.load(f)

    # ----- Load from settings_*.json -----

    if settings.race_type == "ASC":
        config_path = config_directory / "settings_ASC.json"
    else:
        config_path = config_directory / "settings_FSGP.json"

    with open(config_path) as f:
        model_parameters = json.load(f)

    # Build simulation model
    simulation_builder = SimulationBuilder()\
        .set_initial_conditions(initial_conditions)\
        .set_model_parameters(model_parameters, settings.race_type)\
        .set_golang(settings.golang)\
        .set_return_type(settings.return_type)\
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
    bounds = InputBounds()
    bounds.add_bounds(driving_hours, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)
    random_optimization = RandomOptimization(bounds, simulation_model.run_model)

    # Perform optimization with Bayesian optimization
    results = optimization.maximize(init_points=3, n_iter=settings.optimization_iterations, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=settings.verbose,
                                           route_visualization=settings.route_visualization)

    # Perform optimization with random optimization
    results_random = random_optimization.maximize(iterations=settings.optimization_iterations)
    optimized_random = simulation_model.run_model(speed=np.fromiter(results_random, dtype=float), plot_results=True,
                                                  verbose=settings.verbose,
                                                  route_visualization=settings.route_visualization)

    #  ----- Output results ----- #

    display_output(settings.return_type, unoptimized_time, optimized, optimized_random, results, results_random)

    return unoptimized_time


def main():
    """

    This is the entry point to Simulation.
    First, parse command line arguments, then execute simulation optimization sequence.

    """

    #  ----- Parse commands passed from command line ----- #

    cmds = sys.argv
    simulation_settings = parse_commands(cmds)

    print("GoLang is " + str("enabled." if simulation_settings.golang else "disabled."))
    print("Verbose is " + str("on." if simulation_settings.verbose else "off."))
    print("Route visualization is " + str("on." if simulation_settings.route_visualization else "off."))
    print("Optimizing for " + str("time." if simulation_settings.return_type == 0 else "distance."))
    print(f"Will perform {simulation_settings.optimization_iterations} optimization iterations.")

    #  ----- Run simulation ----- #

    run_simulation(simulation_settings)

    print("Simulation has completed.")


def display_output(return_type, unoptimized, optimized, optimized_random, results, results_random):
    if return_type is SimulationReturnType.time_taken:
        print(f'TimeSimulation results. Time Taken: {-1 * unoptimized} seconds, ({str(datetime.timedelta(seconds=int(-1 * unoptimized)))})')
        print(f'Optimized results. Time taken: {-1 * optimized} seconds, ({str(datetime.timedelta(seconds=int(-1 * optimized)))})')
        print(f'Random results. Time taken: {-1 * optimized_random} seconds, ({str(datetime.timedelta(seconds=int(-1 * optimized_random)))})')

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


valid_commands = ["-help", "-race_type", "-golang", "-optimize", "-iter", "-verbose", "-route_visualization", "-granularity"]


def identify_invalid_commands(cmds):
    """

    Check to make sure that commands passed from user are valid.

    :param cmds: list of commands from command line
    :return: the first invalid command detected.

    """

    for cmd in cmds:
        # Make sure is actually a command and not "python3" or "python", which we don't need to handle.
        if not cmd[0] == '-':
            continue

        # Get the identifier of the command, not the argument of it.
        split_cmd = cmd.split('=')
        if not split_cmd[0] in valid_commands:
            return split_cmd[0]

    return False


def parse_commands(cmds):
    """

    Parse commands from command line into parameters for the simulation.

    :param cmds: list of commands from to be parsed into parameters.
    :return: return a SimulationParameters object of defaulted or parsed parameters.

    """

    simulation_settings = SimulationSettings()

    # If the user has requested '-help', display list of valid commands.
    if "-help" in cmds:
        display_commands()
        exit()

    # If an invalid command is detected, exit and let the user know.
    if cmd := identify_invalid_commands(cmds):
        raise AssertionError(f"Command '{cmd}' not found. Please use -help for list of valid commands.")

    # Loop through commands and parse them to assign their values to their respective parameters.
    for cmd in cmds:
        if not cmd[0] == '-':
            continue

        split_cmd = cmd.split('=')

        if split_cmd[0] == '-golang':
            simulation_settings.golang = True if split_cmd[1] == 'True' else False

        elif split_cmd[0] == '-optimize':
            if split_cmd[1] == 'distance' or split_cmd[1] == 'distance_travelled':
                simulation_settings.return_type = SimulationReturnType.distance_travelled
            elif split_cmd[1] == 'time_taken' or split_cmd[1] == 'time':
                simulation_settings.return_type = SimulationReturnType.time_taken
            else:
                raise AssertionError(f"Parameter '{split_cmd[1]}' not identifiable.")

        elif split_cmd[0] == '-iter':
            simulation_settings.optimization_iterations = int(split_cmd[1])

        elif split_cmd[0] == '-verbose':
            simulation_settings.verbose = True if split_cmd[1] == 'True' else False

        elif split_cmd[0] == '-route_visualization':
            simulation_settings.route_visualization = True if split_cmd[1] == 'True' else False

        elif split_cmd[0] == '-race_type':
            if not split_cmd[1] in ['ASC', 'FSGP']:
                raise AssertionError(f"Invalid race type {split_cmd[1]}. Please enter 'ASC' or 'FSGP'.")
            simulation_settings.race_type = split_cmd[1]

        elif split_cmd[0] == '-granularity':
            simulation_settings.granularity = split_cmd[1]

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

    """

    #  ----- Load initial conditions ----- #

    with open(config_directory / "initial_conditions.json") as f:
        initial_conditions = json.load(f)

    # ----- Load from settings_ASC.json -----

    if race_type == "ASC":
        config_path = config_directory / "settings_ASC.json"
    else:
        config_path = config_directory / "settings_FSGP.json"

    with open(config_path) as f:
        model_parameters = json.load(f)

    # Build simulation model
    simulation_builder = SimulationBuilder()\
        .set_initial_conditions(initial_conditions)\
        .set_model_parameters(model_parameters, race_type)\
        .set_golang(golang)\
        .set_return_type(SimulationReturnType.void)\
        .set_granularity(granularity)

    simulation_model = simulation_builder.get()

    driving_hours = simulation_model.get_driving_time_divisions()

    if input_speed is None:
        input_speed = np.array([30] * driving_hours)
    if values is None:
        values = ["default"]

    simulation_model.run_model(speed=input_speed, plot_results=False, verbose=False, route_visualization=False)
    results_array = simulation_model.get_results(values)

    return results_array


if __name__ == "__main__":
    main()

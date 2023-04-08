import datetime

import numpy as np
import json
import sys

from simulation.main.MainSimulation import Simulation, SimulationReturnType
from simulation.optimization.bayesian import BayesianOptimization
from simulation.optimization.random import RandomOptimization
from simulation.utils.InputBounds import InputBounds
from simulation.config import settings_directory
from simulation.common import simulationState

"""
Description: Given a set of driving speeds, find the time required to complete the route specified in the config files. 
"""


class SimulationSettings:
    """
    This class stores settings that will be used in the process of optimizing Simulation.
    """
    def __init__(self, golang=True, return_type=SimulationReturnType.time_taken, optimization_iterations=5):
        self.optimization_iterations = optimization_iterations
        self.golang = golang
        self.return_type = return_type


def main():
    input_speed = np.array([30])

    """
    Simulation automatically reshapes the array depending on the simulation_length. 
    Examples:
      If you want a constant speed for the entire simulation, insert a single element
      into the input_speed array. 
      >>> input_speed = np.array([30]) <-- constant speed of 30km/h
      If you want 50km/h in the first half of the simulation and 60km/h in the second half,
      do the following:
    >>> input_speed = np.array([50, 60])
      Keep in mind, however, that the condition len(input_speed) <= simulation_length must be true
    """

    #  ----- Parse initial conditions ----- #

    with open(settings_directory / "initial_conditions.json") as f:
        args = json.load(f)

    initial_simulation_conditions = simulationState.SimulationState(args)

    #  ----- Parse commands passed from command line ----- #

    cmds = sys.argv
    simulation_settings = parse_commands(cmds)

    print("GoLang is " + str("enabled." if simulation_settings.golang else "disabled."))
    print("Optimizing for " + str("time." if simulation_settings.return_type == 0 else "distance."))
    print(f"Will perform {simulation_settings.optimization_iterations} optimization iterations.")

    #  ----- Begin optimization ----- #

    simulation_model = Simulation(initial_simulation_conditions, simulation_settings.return_type, race_type="ASC")
    unoptimized = simulation_model.run_model(speed=input_speed, plot_results=True,
                                             verbose=False,
                                             route_visualization=False)
    bounds = InputBounds()
    bounds.add_bounds(100, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)
    random_optimization = RandomOptimization(bounds, simulation_model.run_model)

    results = optimization.maximize(init_points=3, n_iter=simulation_settings.optimization_iterations, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=False,
                                           route_visualization=False)
    results_random = random_optimization.maximize(iterations=simulation_settings.optimization_iterations)
    optimized_random = simulation_model.run_model(speed=np.fromiter(results_random, dtype=float), plot_results=True,
                                                  verbose=False,
                                                  route_visualization=False)

    display_results(simulation_settings.return_type, unoptimized, optimized, optimized_random, results, results_random)

    return unoptimized

# ----- Command Line Control ----- #


def display_results(return_type, unoptimized, optimized, optimized_random, results, results_random):
    if return_type is SimulationReturnType.time_taken:
        print(f'TimeSimulation results. Time Taken: {-1 * unoptimized} seconds, ({str(datetime.timedelta(seconds=int(-1 * unoptimized)))})')
        print(f'Optimized results. Time taken: {-1 * optimized} seconds, ({str(datetime.timedelta(seconds=int(-1 * optimized)))})')
        print(f'Random results. Time taken: {-1 * optimized_random} seconds, ({str(datetime.timedelta(seconds=int(-1 * optimized_random)))})')
        print(f'Optimized Speeds array: {results}')
        print(f'Random Speeds array: {results_random}')

    elif return_type is SimulationReturnType.distance_travelled:
        print(f'Distance travelled: {unoptimized}')
        print(f'Optimized results. Max traversable distance: {optimized}')
        print(f'Random results. Max traversable distance: {optimized_random}')
        print(f'Optimized Speeds array: {results}')
        print(f'Random Speeds array: {results_random}')


def display_commands():
    """

    Display all valid command line commands to the user.

    """
    print("---------COMMANDS---------\n"
          "-help     Display list of \n"
          "          valid commands.\n"
          "-golang   Define whether\n"
          "          golang implementations\n"
          "          will be used.\n"
          "-optimize Define what data \n"
          "          the simulation\n"
          "          should optimize.\n"
          "-iter     Set how many\n"
          "          iterations of \n"
          "          optimizations should\n"
          "          be performed on\n"
          "          the simulation.\n"
          "\n"
          "----------EXAMPLE---------\n"
          ">>>python3 fastest_time_given_distance.py -golang=False -optimize=time -iter=3\n")


valid_commands = ["-help", "-golang", "-optimize", "-iter"]


def detect_invalid_commands(cmds):
    """

    Check to make sure that commands passed from user are valid.

    :param cmds: list of commands from command line

    :return: the first invalid command detected.

    """
    for cmd in cmds:
        split_cmd = cmd.split('=')
        if not split_cmd[0] in valid_commands:
            return split_cmd[0]
    return False


def parse_commands(cmds):
    """

    Parse arguments from command line into parameters for the simulation.

    :param cmds: list of commands from to be parsed into parameters.

    :return: return a SimulationParameters object of defaulted or parsed parameters.

    """
    simulation_parameters = SimulationSettings()

    # If the user has requested '-help', display list of valid commands.
    if "-help" in cmds:
        display_commands()
        exit()

    # If an invalid command is detected, exit and let the user know.
    if cmd := detect_invalid_commands(cmds):
        raise AssertionError(f"Command(s) '{cmd}' not found. Please use -help for list of valid commands.")

    # Loop through commands and parse them to assign their values to their respective parameters.
    for cmd in cmds:
        split_cmd = cmd.split('=')

        if split_cmd[0] == '-golang':
            simulation_parameters.golang = True if split_cmd[1] == 'True' else False

        elif split_cmd[0] == '-optimize':
            if split_cmd[1] == 'distance' or split_cmd[1] == 'distance_travelled':
                simulation_parameters.return_type = SimulationReturnType.distance_travelled
            elif split_cmd[1] == 'time_taken' or split_cmd[1] == 'time':
                simulation_parameters.return_type = SimulationReturnType.time_taken
            elif split_cmd[1] == 'results' or split_cmd[1] == 'simulation_results':
                raise AssertionError(f"Return type '{split_cmd[1]}' is not valid for optimization.")
            else:
                raise AssertionError(f"Parameter '{split_cmd[1]}' not identifiable.")

        elif split_cmd[0] == '-iter':
            simulation_parameters.optimization_iterations = int(split_cmd[1])

    return simulation_parameters


if __name__ == "__main__":
    main()

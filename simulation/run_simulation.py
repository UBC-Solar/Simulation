import datetime

import numpy as np
import json
import sys

from main.Simulation import Simulation, SimulationReturnType
from optimization.bayesian import BayesianOptimization
from optimization.random import RandomOptimization
from utils.InputBounds import InputBounds
from config import settings_directory
from common import simulationState

"""
Description: Given a set of driving speeds, find the time required to complete the route specified in the config files. 
"""


class SimulationParameters:
    def __init__(self, golang=True, return_type=SimulationReturnType.distance_travelled, optimization_iterations=5):
        self.optimization_iterations = optimization_iterations
        self.golang = golang
        self.return_type = return_type


def main():
    input_speed = np.array([30])

    """
    Note: it no longer matters how many elements the input_speed array has, the simulation automatically
        reshapes the array depending on the simulation_length. 
    Examples:
      If you want a constant speed for the entire simulation, insert a single element
      into the input_speed array. 
      >>> input_speed = np.array([30]) <-- constant speed of 30km/h
      If you want 50km/h in the first half of the simulation and 60km/h in the second half,
      do the following:
    >>> input_speed = np.array([50, 60])
      This logic will apply for all subsequent array lengths (3, 4, 5, etc.)
      Keep in mind, however, that the condition len(input_speed) <= simulation_length must be true
    """

    #  ----- Parse initial conditions ----- #


    with open(settings_directory / "initial_conditions.json") as f:
        args = json.load(f)

    initial_simulation_conditions = simulationState.SimulationState(args)

    #  ----- Parse commands passed from command line ----- #

    cmds = sys.argv
    simulation_parameters = parse_commands(cmds)

    print("GoLang is " + str("enabled." if simulation_parameters.golang else "disabled."))
    print("Optimizing for " + str("time." if simulation_parameters.return_type == 0 else "distance."))
    print(f"Will perform {simulation_parameters.optimization_iterations} optimization iterations.")

    #  ----- Optimize with Bayesian Optimization ----- #

    simulation_model = Simulation(initial_simulation_conditions, simulation_parameters.return_type,
                                  race_type="ASC",
                                  golang=simulation_parameters.golang)
    unoptimized_time = simulation_model.run_model(speed=input_speed, plot_results=True,
                                                  verbose=False,
                                                  route_visualization=False)
    bounds = InputBounds()
    bounds.add_bounds(8, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)
    random_optimization = RandomOptimization(bounds, simulation_model.run_model)

    results = optimization.maximize(init_points=3, n_iter=simulation_parameters.optimization_iterations, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=False,
                                           route_visualization=False)

    results_random = random_optimization.maximize(iterations=simulation_parameters.optimization_iterations)
    optimized_random = simulation_model.run_model(speed=np.fromiter(results_random, dtype=float), plot_results=True,
                                                  verbose=False,
                                                  route_visualization=False)

    #  ----- Output results ----- #

    display_output(simulation_parameters.return_type, unoptimized_time, optimized, optimized_random, results, results_random)

    return unoptimized_time


def display_output(return_type, unoptimized, optimized, optimized_random, results, results_random):
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

    return unoptimized


def display_commands():
    """
    Display all valid command line arguments to the user.
    """
    print("-----------------COMMANDS----------------\n"
          "-help     Display list of valid commands.\n"
          "\n"
          "-golang   Define whether golang implementations\n"
          "          will be used. \n"
          "          (True/False)\n"
          "\n"
          "-optimize Define what data the simulation\n"
          "          should optimize. \n"
          "          (time_taken/distance_travelled)\n"
          "\n"
          "-iter     Set how many iterations of optimizations\n"
          "          should be performed on the simulation.\n"
          "\n"
          "------------------USAGE------------------\n"
          ">>>python3 run_simulation.py -golang=False -optimize=time_taken -iter=3\n")


valid_commands = ["-help", "-golang", "-optimize", "-iter", "run_simulation.py"]


def identify_invalid_commands(cmds):
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

    Parse commands from command line into parameters for the simulation.

    :param cmds: list of commands from to be parsed into parameters.

    :return: return a SimulationParameters object of defaulted or parsed parameters.

    """
    simulation_parameters = SimulationParameters()

    # If the user has requested '-help', display list of valid commands.
    if "-help" in cmds:
        display_commands()
        exit()

    # If an invalid command is detected, exit and let the user know.
    if cmd := identify_invalid_commands(cmds):
        raise AssertionError(f"Command '{cmd}' not found. Please use -help for list of valid commands.")

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
            else:
                raise AssertionError(f"Parameter '{split_cmd[1]}' not identifiable.")

        elif split_cmd[0] == '-iter':
            simulation_parameters.optimization_iterations = int(split_cmd[1])

    return simulation_parameters


if __name__ == "__main__":
    main()

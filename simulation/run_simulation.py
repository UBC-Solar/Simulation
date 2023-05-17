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
Description: Execute simulation optimization sequence. 
"""


class SimulationSettings:
    """

    This class stores settings that will be used by the simulation.

    """
    def __init__(self, golang=True, return_type=SimulationReturnType.distance_travelled, optimization_iterations=5, route_visualization=False, verbose=False):
        self.optimization_iterations = optimization_iterations
        self.golang = golang
        self.return_type = return_type
        self.route_visualization = route_visualization
        self.verbose = verbose


def run_simulation(simulation_settings):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param SimulationSettings simulation_settings: object that stores settings for the simulation and optimization sequence
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    input_speed = np.array([30])

    #  ----- Parse initial conditions ----- #

    with open(settings_directory / "initial_conditions.json") as f:
        args = json.load(f)

    initial_simulation_conditions = simulationState.SimulationState(args)

    #  ----- Optimize with Bayesian Optimization ----- #

    simulation_model = Simulation(initial_simulation_conditions, simulation_settings.return_type,
                                  race_type="ASC",
                                  golang=simulation_settings.golang)
    unoptimized_time = simulation_model.run_model(speed=input_speed, plot_results=True,
                                                  verbose=simulation_settings.verbose,
                                                  route_visualization=simulation_settings.route_visualization)
    bounds = InputBounds()
    bounds.add_bounds(8, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)
    random_optimization = RandomOptimization(bounds, simulation_model.run_model)

    results = optimization.maximize(init_points=3, n_iter=simulation_settings.optimization_iterations, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=simulation_settings.verbose,
                                           route_visualization=simulation_settings.route_visualization)

    results_random = random_optimization.maximize(iterations=simulation_settings.optimization_iterations)
    optimized_random = simulation_model.run_model(speed=np.fromiter(results_random, dtype=float), plot_results=True,
                                                  verbose=simulation_settings.verbose,
                                                  route_visualization=simulation_settings.route_visualization)

    #  ----- Output results ----- #

    display_output(simulation_settings.return_type, unoptimized_time, optimized, optimized_random, results, results_random)

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
          "route-visualization   Define whether the simulation route\n"
          "                      should be plotted and visualized.\n"
          "                      (True/False)\n"
          "\n"     
          "-------------------------USAGE--------------------------\n"
          ">>>python3 run_simulation.py -golang=False -optimize=time_taken -iter=3\n")


valid_commands = ["-help", "-golang", "-optimize", "-iter", "-verbose", "-route-visualization"]


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

        elif split_cmd[0] == '-route-visualization':
            simulation_settings.route_visualization = True if split_cmd[1] == 'True' else False

    return simulation_settings


if __name__ == "__main__":
    main()

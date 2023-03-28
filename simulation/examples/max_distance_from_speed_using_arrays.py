import numpy as np
import json
import sys

import simulation
from simulation.common import helpers
from simulation.optimization.bayesian import BayesianOptimization
from simulation.common.simulationState import SimulationState
from simulation.optimization.random import RandomOptimization
from simulation.utils.InputBounds import InputBounds
from simulation.config import settings_directory

"""
Description: Given an hourly driving speed, find the range at the speed
before the battery runs out [speed -> distance].
"""


@helpers.timeit
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

    with open(settings_directory / "initial_conditions.json") as f:
        args = json.load(f)

    initialSimulationConditions = SimulationState(args)

    # Parse commands passed from command line, such as "golang=True"
    cmds = sys.argv

    if "-help" in cmds:
        display_commands()
        exit()

    for cmd in cmds:
        split_cmd = cmd.split('=')
        if split_cmd[0] == '-golang':
            if split_cmd[1] == 'True' or split_cmd[1] == 'true' or split_cmd[1] == '1':
                golang = True
            if split_cmd[1] == 'False' or split_cmd[1] == 'false' or split_cmd[1] == '0':
                golang = False

    # If GoLang wasn't explicitly enabled or disabled, default to be enabled.
    try:
        golang
    except:
        golang = True

    print("GoLang is " + str("enabled." if golang else "disabled."))

    simulation_model = simulation.Simulation(initialSimulationConditions, race_type="ASC")
    distance_travelled = simulation_model.run_model(speed=input_speed, plot_results=True, verbose=False, golang=golang)

    bounds = InputBounds()
    bounds.add_bounds(8, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)
    random_optimization = RandomOptimization(
        bounds, simulation_model.run_model)

    results = optimization.maximize(init_points=3, n_iter=1, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=False,
                                           route_visualization=False)

    results_random = random_optimization.maximize(iterations=15)
    optimized_random = simulation_model.run_model(speed=np.fromiter(results_random, dtype=float), plot_results=True,
                                                  verbose=False,
                                                  route_visualization=False)

    print(f'Distance travelled: {distance_travelled}')
    print(f'Optimized results. Max traversable distance: {optimized}')
    print(f'Random results. Max traversable distance: {optimized_random}')
    print(f'Optimized Speeds array: {results}')
    print(f'Random Speeds array: {results_random}')

    return distance_travelled


# Display list of valid command line commands to the user.
def display_commands():
    print("---------COMMANDS---------\n"
          "-help     Display list of \n"
          "          valid commands.\n"
          "-golang   Define whether\n"
          "          golang implementations\n"
          "          will be used.\n")

if __name__ == "__main__":
    main()

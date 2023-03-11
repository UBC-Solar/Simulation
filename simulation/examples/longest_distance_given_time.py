import datetime
import json
import numpy as np

from simulation.common import helpers
from simulation.main.TimeSimulation import TimeSimulation
from simulation.common.simulationState import SimulationState
from simulation.optimization.bayesian import BayesianOptimization
from simulation.utils.InputBounds import InputBounds
from simulation.config import settings_directory

"""
Description: Given a set of driving speeds, find the time required to complete the route specified in the config files. 
"""


@helpers.timeit
def main():
    input_speed = np.array([5])

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

    simulation_model = TimeSimulation(initialSimulationConditions, race_type="ASC")
    time_taken = simulation_model.run_model(speed=input_speed, plot_results=True,
                                            verbose=False,
                                            route_visualization=False)

    bounds = InputBounds()
    bounds.add_bounds(8, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)

    results = optimization.maximize(init_points=1, n_iter=50, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float), plot_results=True,
                                           verbose=False,
                                           route_visualization=False)

    print(
        f'TimeSimulation results. Time Taken: {-1 * time_taken} seconds, ({str(datetime.timedelta(seconds=int(-1 * time_taken)))})')
    print(
        f'Optimized results. Time taken: {-1 * optimized} seconds, ({str(datetime.timedelta(seconds=int(-1 * optimized)))})')
    print(f'Optimized Speeds array: {results}')

    return time_taken


if __name__ == "__main__":
    main()

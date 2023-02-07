import numpy as np

import simulation
from simulation.common import helpers
from simulation.optimization.bayesian import BayesianOptimization
from simulation.optimization.random import RandomOptimization
from simulation.utils.InputBounds import InputBounds

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

    simulation_model = simulation.Simulation(race_type="ASC")
    distance_travelled = simulation_model.run_model(speed=input_speed, plot_results=True, verbose=False)

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


if __name__ == "__main__":
    main()

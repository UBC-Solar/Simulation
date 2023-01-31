import numpy as np

from simulation.common import helpers
from simulation.main import TimeSimulation
from simulation.optimization.bayesian import BayesianOptimization
from simulation.utils.InputBounds import InputBounds
from simulation.main.SimulationResult import SimulationResult

"""
Description: Export Simulation data as a SimulationResults object. 
"""


@helpers.timeit
def main() -> SimulationResult:
    """
    Returns a SimulationResult object with the purpose of exporting simulation data.
    TODO: Add functionality to modify data up to a point in the simulation to allow the simulation to run on real data.
    """

    simulation_model = TimeSimulation(race_type="ASC")

    bounds = InputBounds()
    bounds.add_bounds(8, 20, 60)
    optimization = BayesianOptimization(bounds, simulation_model.run_model)

    # The number of times simulation runs is init_points + n_iter + 1
    results = optimization.maximize(init_points=0, n_iter=0, kappa=10)
    optimized = simulation_model.run_model(speed=np.fromiter(results, dtype=float),
                                           plot_results=False, verbose=False, route_visualization=False,
                                           return_results_object=True)

    return optimized


def GetSimulationData() -> SimulationResult:
    """
    Returns a SimulationResult object with the purpose of exporting simulation data.
    """
    return main()


if __name__ == "__main__":
    main()

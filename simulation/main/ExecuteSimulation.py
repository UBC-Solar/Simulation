import numpy as np
import json

from simulation.main.Simulation import Simulation, SimulationReturnType
from simulation.common.simulationState import SimulationState
from simulation.main.SimulationResult import SimulationResult
from simulation.config import settings_directory


"""
Description: Export Simulation data as a SimulationResults object. 
"""


def GetSimulationData(golang=True):
    """

    Returns a SimulationResult object with the purpose of exporting simulation data.

    """

    input_speed = np.array([30])

    with open(settings_directory / "initial_conditions.json") as f:
        args = json.load(f)

    return_type = SimulationReturnType.simulation_results
    initialSimulationConditions = SimulationState(args)
    simulation_model = Simulation(initialSimulationConditions, return_type, race_type="ASC", golang=golang)

    results = simulation_model.run_model(speed=input_speed, plot_results=False, verbose=False, route_visualization=False)
    map_coordinates = simulation_model.gis.path
    return results, map_coordinates


if __name__ == "__main__":
    results, map_coordinates = GetSimulationData()
    print(map_coordinates[100])
    print(results.time_taken)

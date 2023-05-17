import numpy as np
import json

from simulation.main.Simulation import Simulation, SimulationReturnType
from simulation.common.simulationState import SimulationState
from simulation.main.SimulationResult import SimulationResult
from simulation.config import settings_directory


"""
Description: Export Simulation data as a SimulationResults object. 
"""


def GetSimulationData(golang=True) -> SimulationResult:
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

    return results


if __name__ == "__main__":
    print(GetSimulationData().time_taken)

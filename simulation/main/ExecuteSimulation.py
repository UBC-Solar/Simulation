import numpy as np
import json

from simulation.main.Simulation import SimulationReturnType
from simulation.common.simulationBuilder import SimulationBuilder
from simulation.config import config_directory


"""
Description: Export Simulation data as a SimulationResults object. 
"""


def GetSimulationData(race_type="ASC", golang=True, granularity=1):
    """

    Returns a SimulationResult object with the purpose of exporting simulation data.

    """

    #  ----- Load initial conditions ----- #

    with open(config_directory / "initial_conditions.json") as f:
        initial_conditions = json.load(f)

    # ----- Load from settings_*.json -----

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
        .set_return_type(SimulationReturnType.simulation_results)\
        .set_granularity(granularity)

    simulation_model = simulation_builder.get()

    driving_hours = simulation_model.get_driving_time_divisions()
    input_speed = np.array([30] * driving_hours)

    results = simulation_model.run_model(speed=input_speed, plot_results=False, verbose=False, route_visualization=False)
    map_coordinates = simulation_model.gis.path
    return results, map_coordinates


if __name__ == "__main__":
    results, map_coordinates = GetSimulationData()
    print(map_coordinates[100])
    print(results.time_taken)

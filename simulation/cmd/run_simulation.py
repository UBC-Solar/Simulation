import argparse
import hashlib
import os
import pathlib
import pickle

import numpy as np
import json

from simulation.cache import query_npz_from_cache
from simulation.config import config_directory, speeds_directory
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.model.Simulation import Simulation, SimulationReturnType
from simulation.common.race import Race, load_race, compile_race
from simulation.utils.SimulationBuilder import RaceDataNotMatching
from simulation.cache.race import race_directory
from simulation.utils.hash_util import hash_dict


class SimulationSettings:
    """

    This class stores settings that will be used by the simulation.

    """

    def __init__(self, race_type="FSGP", verbose=False, granularity=1):
        self.race_type = race_type
        self.return_type = SimulationReturnType.distance_and_time
        self.route_visualization = False
        self.verbose = verbose
        self.granularity = granularity





def run_simulation(settings: SimulationSettings, speeds_filename: str, plot_results: bool = True):
    """
    This is the entry point to Simulation.

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param plot_results: plot results of Simulation
    :param SimulationSettings settings: object that stores settings for the simulation and optimization sequence
    :param str speeds_filename: name of the cached speeds file to use, otherwise a default array is used
    :return: returns the time taken for simulation to complete before optimization
    :rtype: Simulation

    """

    # Try to build model, if race data needs updating it will be updated before building
    try:
        simulation_model = build_model(settings)
    except RaceDataNotMatching:
        compile_race(config_directory, race_directory, Race.RaceType[settings.race_type])
        simulation_model = build_model(settings)

    # Initialize a "guess" speed array
    driving_hours = simulation_model.get_driving_time_divisions()

    if speeds_filename is None:
        input_speed = np.array([45] * driving_hours)
    else:
        input_speed = np.load(speeds_directory / (speeds_filename + ".npy"))
        if len(input_speed) != driving_hours:
            raise ValueError(f"Cached speeds {speeds_filename} has improper length!")

    # Run simulation model with the "guess" speed array
    simulation_model.run_model(speed=input_speed, plot_results=plot_results,
                                                  verbose=settings.verbose,
                                                  route_visualization=settings.route_visualization)

    return simulation_model


def run_unoptimized_and_export(input_speed=None, values=None, race_type=Race.FSGP, granularity=1):
    """

    Export simulation data.

    :param input_speed: defaulted to 30km/h, an array of speeds that the Simulation will use.
    :param values: defaulted to what was outputted by now-deprecated SimulationResults object, a tuple of strings that
    each correspond to a value or array that the Simulation will export. See Simulation.get_results() for valid keys.
    :param race_type: define the race type, either "ASC" or "FSGP"
    :param granularity: define the granularity of Simulation speed array
    implementations should be used.
    :param granularity: control how granular the time divisions of Simulation should be
    :param race_type: whether the race is ASC or FSGP

    """

    # Get a basic simulation model
    simulation_model = build_basic_model(race_type, granularity)

    driving_hours = simulation_model.get_driving_time_divisions()
    if input_speed is None:
        input_speed = np.array([30] * driving_hours)
    if values is None:
        values = "default"

    simulation_model.run_model(speed=input_speed, plot_results=True, verbose=False, route_visualization=False,
                               plot_portion=(0.0 / 8.0, 8.0 / 8.0))

    results_array = simulation_model.get_results(values)

    return results_array


def get_default_settings(race_type: Race.RaceType = Race.FSGP) -> tuple[dict, dict]:
    assert race_type in Race.RaceType

    #  ----- Load initial conditions -----
    with open(config_directory / f"initial_conditions_{race_type}.json") as f:
        initial_conditions = json.load(f)

    #  ----- Load model parameters -----
    config_path = config_directory / f"settings_{race_type}.json"
    with open(config_path) as f:
        model_parameters = json.load(f)

    return initial_conditions, model_parameters


def build_basic_model(race_type: Race.RaceType = Race.FSGP, granularity: float = 1) -> Simulation:
    initial_conditions, model_parameters = get_default_settings(race_type)
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.RaceType(race_type)) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(granularity) \
        .set_race_data(load_race(race_type, pathlib.Path(__file__).parent))
    return simulation_builder.get()




def _health_check() -> None:
    """

    This is an entrypoint to run Simulation to validate the installation and that no errors will be raised.

    """

    simulation_model = build_basic_model()

    # Initialize a "guess" speed array
    input_speed = np.array([30] * simulation_model.get_driving_time_divisions())

    # Run simulation model with the "guess" speed array
    simulation_model.run_model(speed=input_speed, plot_results=False,
                               verbose=False,
                               route_visualization=False)

    print("Simulation was successful!")

def build_model(settings: SimulationSettings):

    # Build simulation model
    initial_conditions, model_parameters = get_default_settings(Race.RaceType(settings.race_type))
    weather = query_npz_from_cache("weather", f"weather_data_{Race.RaceType(settings.race_type)}_SOLCAST", match_hash=False)
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.RaceType(settings.race_type)) \
        .set_return_type(settings.return_type) \
        .set_granularity(settings.granularity) \
        .set_race_data(load_race(Race.RaceType(settings.race_type), race_directory)) \
        .set_route_data(query_npz_from_cache("route", f"route_data_{Race.RaceType(settings.race_type)}",
                                             match_hash=False)) \
        .set_weather_forecasts(weather['weather_forecast'])

    return simulation_builder.get()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_type", required=False, default="FSGP", help="Define which race should be simulated. ("
                                                                            "ASC/FSGP)", type=str)
    parser.add_argument("--granularity", required=False, default=1, help="Define how granular the speed array should "
                                                                         "be, where 1 is hourly and 2 is bi-hourly.",
                        type=int)
    parser.add_argument("-v", "--verbose", required=False, default=False, help="Set to nake simulation execute "
                                                                               "as verbose.",
                        action="store_true")

    parser.add_argument('-s', "--speeds", required=False, default=None, help="Name of cached speed array (.npy extension is assumed)", type=str)

    args = parser.parse_args()

    run_simulation(SimulationSettings(race_type=args.race_type, verbose=args.verbose, granularity=args.granularity), speeds_filename=args.speeds)

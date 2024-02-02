import numpy as np
import subprocess
import json
import sys
import csv

from simulation.main import Simulation, SimulationReturnType
from simulation.utils.InputBounds import InputBounds
from simulation.config import config_directory
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.optimization.genetic import GeneticOptimization
from tqdm import tqdm

"""
Description: Execute simulation optimization sequence. 
"""


class SimulationSettings:
    """

    This class stores settings that will be used by the simulation.

    """

    def __init__(self, race_type="ASC", golang=True, return_type=SimulationReturnType.distance_and_time,
                 optimization_iterations=20, route_visualization=False, verbose=False, granularity=1):
        self.race_type = race_type
        self.optimization_iterations = optimization_iterations
        self.golang = golang
        self.return_type = return_type
        self.route_visualization = route_visualization
        self.verbose = verbose
        self.granularity = granularity

    def __str__(self):
        return (f"GoLang is {str('enabled.' if self.golang else 'disabled.')}\n"
                f"Verbose is {str('on.' if self.verbose else 'off.')}\n"
                f"Route visualization is {str('on.' if self.route_visualization else 'off.')}\n"
                f"Optimizing for {str('time.' if self.return_type == 0 else 'distance.')}\n"
                f"Will perform {self.optimization_iterations} optimization iterations.\n")


def main():
    """

    This is the entry point to Simulation.
    First, parse command line arguments, then execute simulation optimization sequence.

    """

    #  ----- Parse commands passed from command line ----- #

    cmds = sys.argv
    simulation_settings = parse_commands(cmds)

    print(str(simulation_settings))

    #  ----- Run simulation ----- #

    run_simulation(simulation_settings)

    print("Simulation has completed.")


def run_simulation(settings):
    """

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param SimulationSettings settings: object that stores settings for the simulation and optimization sequence
    :return: returns the time taken for simulation to complete before optimization
    :rtype: float

    """

    # Build simulation model
    initial_conditions, model_parameters = get_default_settings(settings.race_type)
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, settings.race_type) \
        .set_golang(settings.golang) \
        .set_return_type(settings.return_type) \
        .set_granularity(settings.granularity)

    simulation_model = simulation_builder.get()

    # Initialize a "guess" speed array
    driving_hours = simulation_model.get_driving_time_divisions()
    input_speed = np.array([30] * driving_hours)

    # Run simulation model with the "guess" speed array
    unoptimized_time = simulation_model.run_model(speed=input_speed, plot_results=True,
                                                  verbose=settings.verbose,
                                                  route_visualization=settings.route_visualization)

    # Set up optimization models
    maximum_speed = 80
    minimum_speed = 0

    bounds = InputBounds()
    bounds.add_bounds(driving_hours, minimum_speed, maximum_speed)

    run_hyperparameter_search(simulation_model, bounds)

    return unoptimized_time


def display_commands():
    """

    Display all valid command line arguments to the user.

    """

    print("------------------------COMMANDS-----------------------\n"
          "-help                 Display list of valid commands.\n"
          "\n"
          "-race_type            Define which race should be simulated. \n"
          "                      (ASC/FSGP)\n"
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
          "-route_visualization   Define whether the simulation route\n"
          "                      should be plotted and visualized.\n"
          "                      (True/False)\n"
          "\n"
          "-granularity          Define how granular the speed array\n"
          "                      should be, where 1 is hourly and 2 is\n"
          "                      bi-hourly.\n"
          "\n"
          "-------------------------USAGE--------------------------\n"
          ">>>python3 run_simulation.py -golang=False -optimize=time_taken -iter=3\n")


def parse_commands(cmds) -> SimulationSettings:
    """

    Parse commands from command line into parameters for the simulation.

    :param cmds: list of commands from to be parsed into parameters.
    :return: return a SimulationParameters object of defaulted or parsed parameters.
    :rtype: SimulationSettings

    """

    simulation_settings = SimulationSettings()

    command_to_action = {
        '-golang': lambda x: set_golang(x),
        '-optimize': lambda x: set_return_type(x),
        '-iter': lambda x: set_iterations(x),
        '-verbose': lambda x: set_verbose(x),
        '-route_visualization': lambda x: set_route_visualization(x),
        '-race_type': lambda x: set_race_type(x),
        '-granularity': lambda x: set_granularity(x)
    }

    def set_golang(value: str):
        simulation_settings.golang = True if value == 'True' or value == 'true' else False

    def set_return_type(value: str):
        try:
            simulation_settings.return_type = SimulationReturnType(value)
        except ValueError:
            raise ValueError(f"{value} could not be recognized as a SimulationReturnType!")

    def set_iterations(value: str):
        simulation_settings.optimization_iterations = int(value)

    def set_verbose(value: str):
        simulation_settings.verbose = True if value == 'True' or value == 'true' else False

    def set_route_visualization(value: str):
        simulation_settings.route_visualization = True if value == 'True' or value == 'true' else False

    def set_race_type(value: str):
        assert value in ['ASC', 'FSGP'], f"Invalid race type {value}. Please enter 'ASC' or 'FSGP'."
        simulation_settings.race_type = value

    def set_granularity(value: float):
        simulation_settings.granularity = value

    # If the user has requested '-help', display list of valid commands.
    if "-help" in cmds:
        display_commands()
        exit()

    # Loop through commands and parse them to assign their values to their respective parameters.
    for cmd in cmds:
        if not cmd[0] == '-':
            continue

        split_cmd = cmd.split('=')

        try:
            action = command_to_action[split_cmd[0]]
            action(split_cmd[1])
        except KeyError:
            raise KeyError(f"{cmd} not identified!")

    return simulation_settings


def run_unoptimized_and_export(input_speed=None, values=None, race_type="ASC", granularity=1, golang=True):
    """

    Export simulation data.

    :param input_speed: defaulted to 30km/h, an array of speeds that the Simulation will use.
    :param values: defaulted to what was outputted by now-deprecated SimulationResults object, a tuple of strings that
    each correspond to a value or array that the Simulation will export. See Simulation.get_results() for valid keys.
    :param race_type: define the race type, either "ASC" or "FSGP"
    :param granularity: define the granularity of Simulation speed array
    :param golang: define whether GoLang
    implementations should be used.
    :param granularity: control how granular the time divisions of Simulation should be
    :param race_type: whether the race is ASC or FSGP

    """

    # Get a basic simulation model
    simulation_model = build_basic_model(race_type, golang, granularity)

    driving_hours = simulation_model.get_driving_time_divisions()
    if input_speed is None:
        input_speed = np.array([30] * driving_hours)
    if values is None:
        values = "default"

    simulation_model.run_model(speed=input_speed, plot_results=True, verbose=False, route_visualization=False,
                               plot_portion=(0.0 / 8.0, 8.0 / 8.0))
    results_array = simulation_model.get_results(values)

    return results_array


def run_hyperparameter_search(simulation_model: Simulation, bounds: InputBounds, results_directory: str = "/Simulation/results/"):
    evals_per_setting: int = 1
    settings_file: str = results_directory + "settings.csv"
    results_file: str = results_directory + "results.csv"

    stop_index = 0

    with open(settings_file, 'r') as f:
        csv_reader = csv.reader(f, delimiter=',')
        settings_list = GeneticOptimization.parse_csv_into_settings(csv_reader)

    try:
        with open(results_file, 'x') as f:
            writer = csv.writer(f)
            writer.writerow(["Chromosomes", "Parent_Selection", "Generations", "Parents", "Crossover",
                             "Elitism", "Mutation Type", "Mutation Percent", "Max Mutation"])
    except FileExistsError:
        pass

    total_num = GeneticOptimization.get_total_generations(settings_list) * evals_per_setting
    with tqdm(total=total_num, file=sys.stdout, desc="Running hyperparameter search", position=0, leave=True) as pbar:
        try:
            for settings in settings_list:
                stop_index += 1
                for x in range(evals_per_setting):
                    geneticOptimization = GeneticOptimization(simulation_model, bounds, settings=settings, pbar=pbar,
                                                              plot_fitness=True)
                    geneticOptimization.maximize()
                    best_input: np.ndarray = geneticOptimization.output(results_directory)
                    distanced_travelled, _ = simulation_model.run_model(best_input, plot_results=False)
                    geneticOptimization.write_results(distanced_travelled, results_directory=results_directory)

        except KeyboardInterrupt:
            print(f"Finished {stop_index - 1} setting(s), stopped while evaluating setting {stop_index}.")
            exit()
    print("Hyperparameter search has concluded.")


def get_default_settings(race_type: str = "ASC") -> tuple[dict, dict]:
    assert race_type in ["ASC", "FSGP"]

    #  ----- Load initial conditions -----
    with open(config_directory / f"initial_conditions_{race_type}.json") as f:
        initial_conditions = json.load(f)

    #  ----- Load model parameters -----
    config_path = config_directory / f"settings_{race_type}.json"
    with open(config_path) as f:
        model_parameters = json.load(f)

    return initial_conditions, model_parameters


def build_basic_model(race_type: str = "ASC", golang: bool = True, granularity: float = 1) -> Simulation:
    initial_conditions, model_parameters = get_default_settings(race_type)
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, race_type) \
        .set_golang(golang) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(granularity)
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


def _execute_build_script() -> None:
    """

    This is an entrypoint to execute the build script.

    """

    try:
        subprocess.run(["python", "compile.py"], check=True)

    except subprocess.CalledProcessError:
        exit(1)


if __name__ == "__main__":
    main()

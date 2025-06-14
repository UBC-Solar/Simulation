import argparse
import numpy as np
import tomllib as toml
from simulation.config import SimulationReturnType, ConfigDirectory
from simulation.model.Model import Model
from simulation.model.ModelBuilder import ModelBuilder
from simulation.config import (
    EnvironmentConfig,
    SimulationHyperparametersConfig,
    InitialConditions,
    CarConfig,
)
from numpy.typing import NDArray

def run_simulation(
    competition_name: str,
    plot_results: bool,
    verbose: bool,
    speed_dt: int,
    car: str,
    speeds: NDArray[float] = None,
):
    """
    This is the entry point to Simulation.

    This method parses initial conditions for the simulation and store them in a simulationState object. Then, begin
    optimizing simulation with Bayesian optimization and then random optimization.

    :param speeds:
    :param car: The name of the car to be simulated, should match a config file.
    :param speed_dt:
    :param verbose:
    :param competition_name:
    :param plot_results: plot results of Simulation
    :return: returns the time taken for simulation to complete before optimization
    """

    initial_conditions, environment, car_config = get_default_settings(
        competition_name, car
    )

    hyperparameters = SimulationHyperparametersConfig.build_from(
        {
            "simulation_period": 10,
            "return_type": SimulationReturnType.distance_and_time,
            "speed_dt": speed_dt,
        }
    )
    simulation_model = build_model(
        environment, hyperparameters, initial_conditions, car_config
    )

    # Initialize a "guess" speed array
    driving_laps = simulation_model.num_laps
    if speeds is None:
        speeds = np.array([37] * driving_laps)

    # Run simulation model with the "guess" speed array
    simulation_model.run_model(
        speed=speeds,
        plot_results=plot_results,
        verbose=verbose,
        route_visualization=False,
    )

    return simulation_model


def get_default_settings(
    competition_name: str = "FSGP", car_name: str = "BrightSide"
) -> tuple[InitialConditions, EnvironmentConfig, CarConfig]:
    #  ----- Load initial conditions -----
    config_path = ConfigDirectory / f"initial_conditions_{competition_name}.toml"
    with open(config_path, "rb") as f:
        initial_conditions_data = toml.load(f)
        initial_conditions = InitialConditions.build_from(initial_conditions_data)

    #  ----- Load model parameters -----
    config_path = ConfigDirectory / f"settings_{competition_name}.toml"
    with open(config_path, "rb") as f:
        model_parameters_data = toml.load(f)
        environment_config = EnvironmentConfig.build_from(model_parameters_data)

    #  ----- Load car -----
    config_path = ConfigDirectory / f"{car_name}.toml"
    with open(config_path, "rb") as f:
        car_config_data = toml.load(f)
        car_config = CarConfig.build_from(car_config_data)

    return initial_conditions, environment_config, car_config


def build_model(
    environment: EnvironmentConfig,
    hyperparameters: SimulationHyperparametersConfig,
    initial_conditions: InitialConditions,
    car_config: CarConfig,
) -> Model:
    # Build simulation model
    simulation_builder = (
        ModelBuilder()
        .set_environment_config(
            environment,
            rebuild_weather_cache=False,
            rebuild_route_cache=False,
            rebuild_competition_cache=False,
        )
        .set_hyperparameters(hyperparameters)
        .set_initial_conditions(initial_conditions)
        .set_car_config(car_config)
    )
    simulation_builder.compile()

    return simulation_builder.get()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--race_type",
        required=False,
        default="FSGP",
        help="Define which race should be simulated.",
        type=str,
    )

    parser.add_argument(
        "--granularity",
        required=False,
        default=1,
        type=int,
        help="Define how granular (period) the speed array should be, in seconds per element.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        default=False,
        action="store_true",
        help="Set to nake simulation execute as verbose.",
    )

    parser.add_argument(
        "-p",
        "--plot_results",
        required=False,
        default=True,
        type=bool,
        help="Plot results or not",
    )

    parser.add_argument(
        "--car",
        required=False,
        default="Brightside",
        type=str,
        help="Name of car model",
    )

    args = parser.parse_args()

    run_simulation(
        competition_name=args.race_type,
        verbose=args.verbose,
        speed_dt=args.granularity,
        plot_results=args.plot_results,
        car=args.car,
    )

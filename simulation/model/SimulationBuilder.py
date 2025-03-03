import pathlib
import warnings
import numpy as np
from numpy.typing import NDArray
from simulation.common import Race
from simulation.model.Simulation import Simulation
from simulation.cache import SimulationCache, Cache, RoutePath, RacePath, WeatherPath
from simulation.query import OpenweatherQuery, SolcastQuery, TrackRouteQuery, RoadRouteQuery
from simulation.config import (SimulationHyperparametersConfig, OpenweatherConfig, SolcastConfig,
                               EnvironmentConfig, InitialConditions, Route, CompetitionType)


class SimulationBuilder:
    """

    This builder class is used to easily set the parameters and conditions of Simulation.

    """

    def __init__(self, cache: Cache = None):
        self._compiled = False
        self._cache: Cache = cache if cache is not None else SimulationCache

        self._environment_config: EnvironmentConfig | None = None
        self._hyperparameter_config: SimulationHyperparametersConfig | None = None
        self._initial_conditions: InitialConditions | None = None

        # Environment
        self.race_data = None
        self.route_data = None
        self.weather_forecasts = None
        self.race_type = None
        self.origin_coord = None
        self.dest_coord = None
        self.waypoints = None
        self.race_duration = None
        self.weather_provider = None

        # Initial Conditions
        self.current_coord = None
        self.initial_battery_charge = None

        # Hyperparameters
        self.simulation_period = None
        self.return_type = None
        self.vehicle_speed_period = None

    def set_initial_conditions(self, initial_conditions: InitialConditions):
        self._initial_conditions = initial_conditions

        self.current_coord = initial_conditions.current_coord
        self.initial_battery_charge = initial_conditions.initial_battery_soc

        return self

    def set_hyperparameters(self, hyperparameters: SimulationHyperparametersConfig):
        self._hyperparameter_config = hyperparameters

        return self

    def set_environment_config(self, environment_config: EnvironmentConfig):
        self._environment_config = environment_config

        return self

    def _set_initial_conditions(self):
        initial_conditions = self._initial_conditions

        self.current_coord = initial_conditions.current_coord
        self.initial_battery_charge = initial_conditions.initial_battery_soc

    @staticmethod
    def _truncate_hash(hashed: int, num_chars: int = 12) -> str:
        return str(hashed)[:num_chars]

    def _set_competition_data(self):
        competition_config = self._environment_config.competition_config

        competition_hash = SimulationBuilder._truncate_hash(hash(competition_config))
        competition_data_path = RacePath / competition_hash

        # Try to find cached race data
        try:
            race = self._cache.get(competition_data_path)

        # Generate new race data
        except KeyError:
            race = Race(competition_config)
            self._cache.put(race, competition_data_path)

            print(f"Compiling {race.race_type} race")

        self.race_data = race
        self.race_type = competition_config.competition_type

    def _set_hyperparameters(self):
        self.vehicle_speed_period = self._hyperparameter_config.vehicle_speed_period
        self.simulation_period = self._hyperparameter_config.simulation_period
        self.return_type = self._hyperparameter_config.return_type

    def _set_route_data(self):
        competition_config = self._environment_config.competition_config
        route_hash = SimulationBuilder._truncate_hash(competition_config.route_hash())
        route_data_path = RoutePath / route_hash

        coordinates = competition_config.route.coordinates

        # Acquire speed limits
        try:
            speed_limits_per_coordinate: NDArray = self._cache.get(pathlib.Path("route") / "speed_constraints")

        except KeyError:
            warnings.warn("Did not find any cached speed constraints at route/speed_constraints! "
                          "Using 1000km/h as a dummy constraint. Please see docs/SPEED_CONSTRAINTS.md")
            speed_limits_per_coordinate = np.full((len(coordinates),), fill_value=1000.)

        # Try to find cached route data
        try:
            route: Route = self._cache.get(route_data_path)

        # Generate new route data data
        except KeyError:
            match competition_config.competition_type:
                case CompetitionType.TrackCompetition:
                    query = TrackRouteQuery(competition_config)
                case CompetitionType.RoadCompetition:
                    query = RoadRouteQuery(competition_config)
                case _:
                    raise ValueError(f"Unknown Competition Type: {competition_config.competition_type}")

            path_time_zones, path_elevations, coordinates, tiling = query.make()

            route = Route(
                speed_limits=speed_limits_per_coordinate,
                path_elevations=path_elevations,
                path_time_zones=path_time_zones,
                tiling=tiling,
            )

            self._cache.put(route, route_data_path)

            print(f"Queried route data")

        self.route_data = route
        self.origin_coord = route.coords[0]
        self.dest_coord = route.coords[-1]
        self.waypoints = route.coords[1:-1]  # Get all coords between first and last coordinate

    def _set_weather_data(self):
        environment_config = self._environment_config

        environment_hash = SimulationBuilder._truncate_hash(hash(environment_config))
        weather_data_path = WeatherPath / environment_hash

        weather_query_config = environment_config.weather_query_config
        competition_config = environment_config.competition_config

        # Try to find cached weather data
        try:
            weather_data = self._cache.get(weather_data_path)

        # Generate new weather data
        except KeyError:
            if isinstance(weather_query_config, OpenweatherConfig):
                query = OpenweatherQuery(environment_config)
            elif isinstance(weather_query_config, SolcastConfig):
                query = SolcastQuery(environment_config)
            else:
                raise ValueError(f"WeatherConfig type {type(weather_query_config).__name__} "
                                 f"does not have a supported querying method!")

            weather_data = query.make()
            self._cache.put(weather_data, weather_data_path)

            print(f"Queried weather data")

        self.weather_forecasts = weather_data
        self.race_duration = len(competition_config.time_ranges.keys())
        self.weather_provider = weather_query_config.weather_provider

    def compile(self):
        self._set_competition_data()
        self._set_weather_data()
        self._set_route_data()
        self._set_initial_conditions()
        self._set_hyperparameters()

        self._compiled = True

        return self

    def get(self):
        """
        Returns a Simulation object if race data matches the model parameters' hash.
        Compares the hash of race data with model parameters. Raises RaceDataNotMatching if they differ.

        Returns:
            Simulation: A new Simulation object.

        Raises:
            RaceDataNotMatching: If hashes do not match.
            """
        pass

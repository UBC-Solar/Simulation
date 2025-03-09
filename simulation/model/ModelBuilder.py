import pathlib
import warnings
import numpy as np
from numpy.typing import NDArray
from dotenv import load_dotenv
from simulation.common import Race
from haversine import haversine, Unit
from simulation.cache import SimulationCache, Cache, RoutePath, RacePath, WeatherPath
from simulation.config import CarConfig, WeatherProvider, SimulationReturnType
from simulation.query import OpenweatherQuery, SolcastQuery, TrackRouteQuery, RoadRouteQuery
from simulation.config import (SimulationHyperparametersConfig, OpenweatherConfig, SolcastConfig,
                               EnvironmentConfig, InitialConditions, Route, CompetitionType)

from physics.models.arrays import BaseArray, BasicArray
from physics.models.battery import BaseBattery, BasicBattery
from physics.models.lvs import BaseLVS, BasicLVS
from physics.models.motor import BaseMotor, BasicMotor
from physics.models.regen import BaseRegen, BasicRegen
from typing import Optional
from physics.environment.gis import BaseGIS, GIS
from physics.environment.meteorology import BaseMeteorology, IrradiantMeteorology, CloudedMeteorology

load_dotenv()


class ModelBuilder:
    """

    This builder class is used to easily set the parameters and conditions of Simulation.

    """

    def __init__(self, cache: Cache = None):
        self._compiled = False
        self._cache: Cache = cache if cache is not None else SimulationCache

        self._environment_config: Optional[EnvironmentConfig] = None
        self._hyperparameter_config: Optional[SimulationHyperparametersConfig] = None
        self._initial_conditions: Optional[InitialConditions] = None
        self._car_config: Optional[CarConfig] = None

        # Components
        self.array: Optional[BaseArray] = None
        self.lvs: Optional[BaseLVS] = None
        self.gis: Optional[BaseGIS] = None
        self.meteorology: Optional[BaseMeteorology] = None
        self.motor: Optional[BaseMotor] = None
        self.battery: Optional[BaseBattery] = None
        self.regen: Optional[BaseRegen] = None

        # Environment
        self.race_data: Optional[Race] = None
        self.route_data: Optional[Route] = None
        self.weather_forecasts: Optional[NDArray] = None
        self.origin_coord: Optional[NDArray] = None
        self.dest_coord: Optional[NDArray] = None
        self.waypoints: Optional[NDArray] = None
        self.race_duration: Optional[int] = None
        self.weather_provider: Optional[WeatherProvider] = None

        # Initial Conditions
        self.current_coord: Optional[NDArray] = None
        self.initial_battery_charge: Optional[float] = None

        # Hyperparameters
        self.simulation_period: Optional[int] = None
        self.return_type: Optional[SimulationReturnType] = None
        self.vehicle_speed_period: Optional[int] = None

    def set_initial_conditions(self, initial_conditions: InitialConditions):
        self._initial_conditions = initial_conditions

        return self

    def set_hyperparameters(self, hyperparameters: SimulationHyperparametersConfig):
        self._hyperparameter_config = hyperparameters

        return self

    def set_environment_config(self, environment_config: EnvironmentConfig):
        self._environment_config = environment_config

        return self

    def set_car_config(self, car_config: CarConfig):
        self._car_config = car_config

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

        competition_hash = ModelBuilder._truncate_hash(hash(competition_config))
        competition_data_path = RacePath / competition_hash

        # Try to find cached race data
        try:
            race = self._cache.get(competition_data_path)
            raise KeyError
        # Generate new race data
        except KeyError:
            race = Race(competition_config)
            self._cache.put(race, competition_data_path)

            print(f"Compiling {race.race_type} race")

        self.race_data = race

    def _set_hyperparameters(self):
        self.vehicle_speed_period = self._hyperparameter_config.vehicle_speed_period
        self.simulation_period = self._hyperparameter_config.simulation_period
        self.return_type = self._hyperparameter_config.return_type

    def _set_car(self):
        pass

    @staticmethod
    def _calculate_path_distances(coords):
        """

        Obtain the distance between each coordinate by approximating the spline between them
        as a straight line, and use the Haversine formula (https://en.wikipedia.org/wiki/Haversine_formula)
        to calculate distance between coordinates on a sphere.

        :param np.ndarray coords: A NumPy array [n][latitude, longitude]
        :returns path_distances: a NumPy array [n-1][distances],
        :rtype: np.ndarray

        """

        coords_offset = np.roll(coords, (1, 1))
        path_distances = []
        for u, v in zip(coords, coords_offset):
            path_distances.append(haversine(u, v, unit=Unit.METERS))

        return np.array(path_distances)

    @staticmethod
    def _closest_index(target_distance, distances):
        return np.argmin(np.abs(distances - target_distance))

    @staticmethod
    def _calculate_speed_limits(path, speed_limits_per_coordinate) -> np.ndarray:
        cumulative_path_distances = np.cumsum(ModelBuilder._calculate_path_distances(path))
        speed_limits = np.empty([int(cumulative_path_distances[-1]) + 1], dtype=int)

        for position in range(int(cumulative_path_distances[-1]) + 1):
            gis_index = ModelBuilder._closest_index(position, cumulative_path_distances)
            speed_limit = speed_limits_per_coordinate[gis_index]
            speed_limits[position] = speed_limit

        return speed_limits

    def _set_route_data(self):
        competition_config = self._environment_config.competition_config
        route_hash = ModelBuilder._truncate_hash(competition_config.route_hash())
        route_data_path = RoutePath / route_hash

        coordinates = competition_config.route_config.coordinates

        # Acquire speed limits
        try:
            speed_limits_per_coordinate: NDArray = self._cache.get(pathlib.Path("route") / "speed_constraints")

        except KeyError:
            warnings.warn("Did not find any cached speed constraints at route/speed_constraints! "
                          "Using 1000km/h as a dummy constraint. Please see docs/SPEED_CONSTRAINTS.md")
            speed_limits_per_coordinate = np.full((len(coordinates),), fill_value=1000.)

        speed_limits = ModelBuilder._calculate_speed_limits(coordinates, speed_limits_per_coordinate)

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
                speed_limits=speed_limits,
                path_elevations=path_elevations,
                path_time_zones=path_time_zones,
                coords=coordinates,
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

        environment_hash = ModelBuilder._truncate_hash(hash(environment_config))
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

        self.array = BasicArray(
            **self._car_config.array_config.model_dump()
        )

        # The consumed_energy argument does not do anything, which is why it is set to zero.
        self.lvs = BasicLVS(
            0,
            **self._car_config.lvs_config.model_dump()
        )

        match self._car_config.battery_config.battery_type:
            case "BasicBattery":
                self.battery = BasicBattery(
                    self.initial_battery_charge,
                    **self._car_config.battery_config.model_dump()
                )

            # case "BatteryModel":
            #     self.battery = BatteryModel(
            #         self._car_config.battery_config,
            #         self.initial_battery_charge
            #     )

        self.motor = BasicMotor(
            vehicle_mass=self._car_config.vehicle_config.vehicle_mass,
            **self._car_config.motor_config.model_dump()
        )

        self.regen = BasicRegen(
            self._car_config.vehicle_config.vehicle_mass
        )

        tiling = self.route_data.tiling
        route_data = {
            "path": np.tile(self.route_data.coords, (tiling, 1)),
            "num_unique_coords": len(self.route_data.coords),
            "time_zones": np.tile(self.route_data.path_time_zones, tiling),
            "elevations": np.tile(self.route_data.path_elevations, tiling),
        }

        self.gis = GIS(
            route_data,
            self.origin_coord,
            self.current_coord
        )

        match self.weather_provider:
            case WeatherProvider.Solcast:
                self.meteorology = IrradiantMeteorology(
                    race=self.race_data,
                    weather_forecasts=self.weather_forecasts
                )

            case WeatherProvider.Openweather:
                # TODO: We are forcing Solcast use
                self.meteorology = IrradiantMeteorology(
                    race=self.race_data,
                    weather_forecasts=self.weather_forecasts
                )

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
        # We do a delayed import because we want to avoid a circular import. We want Model to have access to
        # ModelBuilder so that type hints work properly.
        from simulation.model.Model import Model

        return Model(
            return_type=self.return_type,
            race=self.race_data,
            speed_dt=self.vehicle_speed_period,
            simulation_dt=self.simulation_period,
            speed_limits=self.route_data.speed_limits,
            array=self.array,
            battery=self.battery,
            motor=self.motor,
            lvs=self.lvs,
            regen=self.regen,
            gis=self.gis,
            meteorology=self.meteorology,
        )

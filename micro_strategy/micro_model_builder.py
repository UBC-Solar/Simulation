import pathlib
import numpy as np
from typing import Optional
from dotenv import load_dotenv
from numpy.typing import NDArray
from haversine import haversine, Unit

from simulation.race import Race, Route
from simulation.query import TrackRouteQuery, RoadRouteQuery
from simulation.config import (
    CarConfig,
    EnvironmentConfig,
    InitialConditions,
    CompetitionType,
)
from simulation.cache import SimulationCache, Cache, RoutePath, RacePath
from physics.models.motor import AdvancedMotor
from physics.environment.gis import GIS

load_dotenv()

class MicroModelBuilder:
    def __init__(self, cache: Cache = None):
        self._compiled = False
        self._cache: Cache = cache if cache is not None else SimulationCache

        self._environment_config: Optional[EnvironmentConfig] = None
        self._initial_conditions: Optional[InitialConditions] = None
        self._car_config: Optional[CarConfig] = None

        self.advanced_motor: Optional[AdvancedMotor] = None
        self.gis: Optional[GIS] = None

        self._rebuild_route_cache: bool = False
        self._rebuild_competition_cache: bool = False

        self.origin_coord: Optional[NDArray] = None
        self.current_coord: Optional[NDArray] = None
        self.route_data: Optional[Route] = None
        self.race_data: Optional[Race] = None
        self.initial_battery_charge: Optional[float] = None

    def set_initial_conditions(self, initial_conditions: InitialConditions):
        self._initial_conditions = initial_conditions
        return self

    def set_environment_config(
        self,
        environment_config: EnvironmentConfig,
        rebuild_weather_cache: bool = False,
        rebuild_competition_cache: bool = False,
        rebuild_route_cache: bool = False,
    ):
        self._environment_config = environment_config
        self._rebuild_route_cache = rebuild_route_cache
        self._rebuild_competition_cache = rebuild_competition_cache
        return self

    def set_car_config(self, car_config: CarConfig):
        self._car_config = car_config
        return self

    def _truncate_hash(self, hashed: int, num_chars: int = 12) -> str:
        return str(hashed)[:num_chars]

    def _calculate_path_distances(self, coords):
        coords_offset = np.roll(coords, (1, 1))
        path_distances = [haversine(u, v, unit=Unit.METERS) for u, v in zip(coords, coords_offset)]
        return np.array(path_distances)

    def _closest_index(self, target_distance, distances):
        return np.argmin(np.abs(distances - target_distance))

    def _calculate_speed_limits(self, path, speed_limits_per_coordinate) -> np.ndarray:
        cumulative_path_distances = np.cumsum(self._calculate_path_distances(path))
        speed_limits = np.empty([int(cumulative_path_distances[-1]) + 1], dtype=int)
        for position in range(int(cumulative_path_distances[-1]) + 1):
            gis_index = self._closest_index(position, cumulative_path_distances)
            speed_limits[position] = speed_limits_per_coordinate[gis_index]
        return speed_limits

    def _set_route_data(self):
        config = self._environment_config.competition_config
        route_hash = self._truncate_hash(config.route_hash())
        route_data_path = RoutePath / route_hash
        coordinates = config.route_config.coordinates

        try:
            speed_limits_per_coordinate = self._cache.get(pathlib.Path("route") / "speed_constraints")
        except KeyError:
            speed_limits_per_coordinate = np.full((len(coordinates),), fill_value=1000.0)

        speed_limits = self._calculate_speed_limits(coordinates, speed_limits_per_coordinate)

        try:
            if self._rebuild_route_cache:
                raise KeyError()
            route: Route = self._cache.get(route_data_path)
        except KeyError:
            match config.competition_type:
                case CompetitionType.TrackCompetition:
                    query = TrackRouteQuery(config)
                case CompetitionType.RoadCompetition:
                    query = RoadRouteQuery(config)
                case _:
                    raise ValueError(f"Unknown Competition Type: {config.competition_type}")

            tz, elev, coords, tiling = query.make()
            route = Route(
                speed_limits=speed_limits,
                path_elevations=elev,
                path_time_zones=tz,
                coords=coords,
                tiling=tiling,
            )
            self._cache.put(route, route_data_path)

        self.route_data = route
        self.origin_coord = route.coords[0]
        self.current_coord = self._initial_conditions.current_coord

    def _set_competition_data(self):
        config = self._environment_config.competition_config
        competition_hash = self._truncate_hash(hash(config))
        competition_data_path = RacePath / competition_hash

        try:
            if self._rebuild_competition_cache:
                raise KeyError()
            race = self._cache.get(competition_data_path)
        except KeyError:
            race = Race(config)
            self._cache.put(race, competition_data_path)

        self.race_data = race

    def compile(self):
        if not all([self._environment_config, self._initial_conditions, self._car_config]):
            raise RuntimeError("Missing configuration before compiling")

        self.initial_battery_charge = self._initial_conditions.initial_battery_soc

        self._set_route_data()
        self._set_competition_data()

        route = self.route_data
        tiling = route.tiling
        route_data = {
            "path": np.tile(route.coords, (tiling, 1)),
            "num_unique_coords": len(route.coords),
            "time_zones": np.tile(route.path_time_zones, tiling),
            "elevations": np.tile(route.path_elevations, tiling),
        }

        self.gis = GIS(route_data, self.origin_coord, self.current_coord)

        self.advanced_motor = AdvancedMotor(
            vehicle_mass=self._car_config.vehicle_config.vehicle_mass,
            **self._car_config.motor_config.model_dump(),
        )

        self._compiled = True
        return self

    def get(self):
        if not self._compiled:
            raise RuntimeError("Model not compiled. Call `compile()` first.")
        return self.advanced_motor, self.gis

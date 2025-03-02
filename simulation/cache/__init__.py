from .cache import (
    FSCache,
    Cache
)

import pathlib

SimulationCache: Cache = FSCache(pathlib.Path(__file__).parent)
RoutePath: pathlib.Path = pathlib.Path("route")
WeatherPath: pathlib.Path = pathlib.Path("weather")
RacePath: pathlib.Path = pathlib.Path("race")

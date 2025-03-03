import pathlib

from ._config import (
    Config,
    ConfigDict
)

from ._track import (
    CompetitionConfig,
    TrackCompetitionConfig,
    CompetitionType,
    RouteConfig,
    Route
)

from ._conditions import (
    InitialConditions
)

from ._weather import (
    WeatherQuery,
    WeatherProvider,
    SolcastConfig,
    OpenweatherConfig,
    OpenweatherPeriod,
    SolcastWeatherPeriod
)

from ._environment import (
    EnvironmentConfig
)

from ._hyperparameters import (
    SimulationHyperparametersConfig,
    SimulationReturnType
)


config_directory = pathlib.Path(__file__).parent
speeds_directory = config_directory / "speeds"

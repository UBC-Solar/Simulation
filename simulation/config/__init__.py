import pathlib


from .models import (
    Config,
    ConfigDict,
    SimulationHyperparametersConfig,
    SimulationReturnType,
    ArrayConfig,
    LVSConfig,
    BatteryConfig,
    BasicBatteryConfig,
    BatteryModelConfig,
    MotorConfig,
    RegenConfig,
    VehicleConfig,
    CarConfig,
    EnvironmentConfig,
    WeatherQuery,
    WeatherProvider,
    SolcastConfig,
    OpenweatherConfig,
    OpenweatherPeriod,
    InitialConditions,
    CompetitionConfig,
    TrackCompetitionConfig,
    CompetitionType,
    RouteConfig,
)

ConfigDirectory = pathlib.Path(__file__).parent
speeds_directory = ConfigDirectory / "speeds_directory"  # Points to speeds_directory


__all__ = [
    "Config",
    "ConfigDict",
    "SimulationHyperparametersConfig",
    "SimulationReturnType",
    "ArrayConfig",
    "LVSConfig",
    "BatteryConfig",
    "BasicBatteryConfig",
    "BatteryModelConfig",
    "MotorConfig",
    "RegenConfig",
    "VehicleConfig",
    "CarConfig",
    "EnvironmentConfig",
    "WeatherQuery",
    "WeatherProvider",
    "SolcastConfig",
    "OpenweatherConfig",
    "OpenweatherPeriod",
    "InitialConditions",
    "CompetitionConfig",
    "TrackCompetitionConfig",
    "CompetitionType",
    "RouteConfig",
]

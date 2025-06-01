from strenum import StrEnum
from enum import Enum
from simulation.config.models import Config, ConfigDict
from data_tools.query import SolcastPeriod


# Enum to discretize between different weather providers we have available
class WeatherProvider(StrEnum):
    Solcast = "Solcast"
    Openweather = "Openweather"


class OpenweatherPeriod(StrEnum):
    Current = "Current"
    Hourly = "Hourly"
    Daily = "Daily"


class WeatherQuery(Config):
    """
    Configuration required to specify how weather forecasts should be queried
    """

    model_config = ConfigDict(frozen=True, subclass_field="weather_provider")

    weather_provider: (
        WeatherProvider  # The resource that will provide weather forecasts
    )


class OpenweatherConfig(WeatherQuery):
    weather_period: (
        OpenweatherPeriod  # The period of weather forecasts (hourly/daily/current)
    )


class SolcastConfig(WeatherQuery):
    weather_period: SolcastPeriod

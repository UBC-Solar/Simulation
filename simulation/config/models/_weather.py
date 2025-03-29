from strenum import StrEnum
from enum import Enum
from simulation.config.models import Config, ConfigDict


# Enum to discretize between different weather providers we have available
class WeatherProvider(StrEnum):
    Solcast = "Solcast"
    Openweather = "Openweather"


class OpenweatherPeriod(StrEnum):
    Current = "Current"
    Hourly = "Hourly"
    Daily = "Daily"


class WeatherQuery(Config):
    model_config = ConfigDict(frozen=True, subclass_field="weather_provider")

    weather_provider: (
        WeatherProvider  # The resource that will provide weather forecasts
    )


class OpenweatherConfig(WeatherQuery):
    weather_period: (
        OpenweatherPeriod  # The period of weather forecasts (hourly/daily/current)
    )


# Class to represent the temporal granularity of Solcast weather API
class SolcastWeatherPeriod(Enum):
    min_5 = "5min"
    min_10 = "10min"
    min_15 = "15min"
    min_20 = "20min"
    min_30 = "30min"
    min_60 = "60min"


SolcastWeatherPeriod_to_formatted = {
    SolcastWeatherPeriod.min_5: {"formatted": "PT5M", "hourly_rate": 20},
    SolcastWeatherPeriod.min_10: {"formatted": "PT10M", "hourly_rate": 6},
    SolcastWeatherPeriod.min_15: {"formatted": "PT15M", "hourly_rate": 4},
    SolcastWeatherPeriod.min_20: {"formatted": "PT20M", "hourly_rate": 3},
    SolcastWeatherPeriod.min_30: {"formatted": "PT30M", "hourly_rate": 2},
    SolcastWeatherPeriod.min_60: {"formatted": "PT60M", "hourly_rate": 1},
}


class SolcastConfig(WeatherQuery):
    weather_period: SolcastWeatherPeriod

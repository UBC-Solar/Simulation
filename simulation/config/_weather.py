from datetime import datetime
from typing import Tuple, Mapping, List, Dict
from strenum import StrEnum
from enum import Enum
from simulation.config import Config, ConfigDict, CompetitionConfig
from pydantic import BaseModel
from numpy.typing import NDArray


# Enum to discretize between different weather providers we have available
class WeatherProvider(StrEnum):
    Solcast = "Solcast"
    Openweather = "Openweather"


class OpenweatherPeriod(StrEnum):
    Current = 1
    Hourly = 54
    Daily = 8


class WeatherConfig(Config):
    model_config = ConfigDict(frozen=True, subclass_type="weather_provider")

    weather_provider: WeatherProvider      # The resource that will provide weather forecasts


class OpenweatherConfig(WeatherConfig):
    weather_period: OpenweatherPeriod      # The period of weather forecasts (hourly/daily/current)


# Class to represent the temporal granularity of Solcast weather API
class SolcastWeatherPeriod(StrEnum):
    class Period(StrEnum):
        min_5 = '5min'
        min_10 = '10min'
        min_15 = '15min'
        min_20 = '20min'
        min_30 = '30min'
        min_60 = '60min'

    possible_periods: dict[Period, dict[str, float | str]] = {
        Period.min_5: {
            'formatted': 'PT5M',
            'hourly_rate': 20
        },
        Period.min_10: {
            'formatted': 'PT10M',
            'hourly_rate': 6
        },
        Period.min_15: {
            'formatted': 'PT15M',
            'hourly_rate': 4
        },
        Period.min_20: {
            'formatted': 'PT20M',
            'hourly_rate': 3
        },
        Period.min_30: {
            'formatted': 'PT30M',
            'hourly_rate': 2
        },
        Period.min_60: {
            'formatted': 'PT60M',
            'hourly_rate': 1
        }
    }


class SolcastConfig(WeatherConfig):
    weather_provider: SolcastWeatherPeriod

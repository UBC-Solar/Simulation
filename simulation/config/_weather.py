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
    Current = "Current"
    Hourly = "Hourly"
    Daily = "Daily"


class WeatherQuery(Config):
    model_config = ConfigDict(frozen=True, subclass_field="weather_provider")

    weather_provider: WeatherProvider      # The resource that will provide weather forecasts


class OpenweatherConfig(WeatherQuery):
    weather_period: OpenweatherPeriod      # The period of weather forecasts (hourly/daily/current)


# Class to represent the temporal granularity of Solcast weather API
class SolcastWeatherPeriod(Enum):
    class Period(StrEnum):
        min_5 = '5min'
        min_10 = '10min'
        min_15 = '15min'
        min_20 = '20min'
        min_30 = '30min'
        min_60 = '60min'

    min_5 = {
        'formatted': 'PT5M',
        'hourly_rate': 20
    }

    min_10 = {
        'formatted': 'PT10M',
        'hourly_rate': 6
    }

    min_15 = {
        'formatted': 'PT15M',
        'hourly_rate': 4
    }

    min_20 = {
        'formatted': 'PT20M',
        'hourly_rate': 3
    }

    min_30 = {
        'formatted': 'PT30M',
        'hourly_rate': 2
    }

    min_60 = {
        'formatted': 'PT60M',
        'hourly_rate': 1
    }


class SolcastConfig(WeatherQuery):
    weather_provider: SolcastWeatherPeriod

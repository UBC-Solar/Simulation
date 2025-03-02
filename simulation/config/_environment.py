from datetime import datetime
from typing import Tuple, Mapping, List, Dict
from strenum import StrEnum
from enum import Enum
from simulation.config import Config, ConfigDict, CompetitionConfig, WeatherConfig
from pydantic import BaseModel
from numpy.typing import NDArray


class EnvironmentConfig(Config):
    model_config = ConfigDict(frozen=True)

    competition_config: CompetitionConfig  # The competition that data is being requisitioned for
    weather_config: WeatherConfig



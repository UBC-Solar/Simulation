from datetime import datetime
from typing import Tuple, Mapping, List, Dict
from strenum import StrEnum
from enum import Enum
from simulation.config import Config, ConfigDict, CompetitionConfig, WeatherQuery
from pydantic import BaseModel
from numpy.typing import NDArray
from anytree.exporter import DotExporter
from anytree import Node, RenderTree


class EnvironmentConfig(Config):
    model_config = ConfigDict(frozen=True)

    competition_config: CompetitionConfig  # The competition that data is being requisitioned for
    weather_query_config: WeatherQuery


if __name__ == "__main__":
    tree = EnvironmentConfig.tree()

    try:
        DotExporter(tree).to_picture("tree.png")

    except FileNotFoundError:
        print("GraphiViz is missing, and is a system dependency to build the configuration tree!")

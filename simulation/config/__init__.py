import pathlib

from ._config import (
    Config,
    ConfigDict
)

from ._track import (
    CompetitionConfig,
    CompetitionType
)


config_directory = pathlib.Path(__file__).parent
speeds_directory = config_directory / "speeds"

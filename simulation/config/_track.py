from datetime import datetime
from typing import Tuple, Mapping, List, Dict
from strenum import StrEnum
from simulation.config import Config, ConfigDict


class RouteConfig(Config):
    model_config = ConfigDict(frozen=True)

    coordinates: List[Tuple[float, float]]              # A list[n] of the n coordinates (latitude, longitude)


class CompetitionType(StrEnum):
    """
    Enum to discretize the different types of competitions that UBC Solar competes in
    """
    TrackCompetition = "TrackCompetition"
    RoadCompetition = "RoadCompetition"


class CompetitionConfig(Config):
    """
    A model which contains the information required to describe a competition
    """
    model_config = ConfigDict(frozen=True, subclass_field="competition_type")

    competition_type: CompetitionType                   # The type of competition
    route: RouteConfig                                  # The route that the competition will follow
    # charging_times: Mapping[int, Tuple[float, float]]   # A map from the day number to the start and end time for charging in seconds from midnight in local time of the origin
    # driving_times: Mapping[int, Tuple[float, float]]    # A map from the day number to the start and end time for driving in seconds from midnight in local time of the origin
    date: datetime                                      # The beginning date that the competition will take place (day/month/year)


class TrackCompetitionConfig(CompetitionConfig):
    """
    A model which contains the information required
    """
    tiling: int                                         # The number of times to tile the route to build the route


class RoadCompetitionConfig(CompetitionConfig):
    """
    A model which contains the information required
    """
    tiling: int                                         # The number of times to tile the route to build the route


class RoadCompetition:
    def __init__(self, config: RoadCompetitionConfig):
        pass


class TrackCompetition:
    def __init__(self, config: TrackCompetitionConfig):
        pass


if __name__ == "__main__":
    config_dict = {
        "competition_type": "TrackCompetition",
        "date": datetime.now(),
        "route": {"coordinates": [(10, 10), (5, 5), (3, 3)]},
        "tiling": 100
    }
    competition_config = CompetitionConfig.build_from(config_dict)

    pass

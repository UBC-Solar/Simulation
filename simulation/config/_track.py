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

    competition_type: CompetitionType   # The type of competition
    route: RouteConfig                  # The route that the competition will follow
    date: datetime                      # The beginning date that the competition will take place (day/month/year)

    # A map from the day number and then some activity ("charging", "driving) to a 2-tuple where the first
    # element is the time since midnight in seconds where the activity is allowed, and the last element is
    # the time, in the same format, where the activity is no longer allowed.
    # Ex. [1, "charging"] -> (32400, 61200) means that on day 1, charging is allowed from 9AM to 5PM.
    time_ranges: Mapping[int, Mapping[str, Tuple[float, float]]]


class TrackCompetitionConfig(CompetitionConfig):
    """
    A model which contains the information required
    """
    tiling: int                                         # The number of times to tile the route to build the route


class RoadCompetitionConfig(CompetitionConfig):
    """
    A model which contains the information required
    """
    pass


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

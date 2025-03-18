from datetime import datetime
from typing import Tuple, Mapping, List
from strenum import StrEnum
from simulation.config.models import Config, ConfigDict


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

    competition_name: str               # The name of the competition
    competition_type: CompetitionType   # The type of competition
    route_config: RouteConfig           # The route that the competition will follow
    date: datetime                      # The beginning date that the competition will take place (day/month/year)

    # A map from some activity ("charging", "driving") and then the day number to a 2-tuple where the first
    # element is the time since midnight in seconds where the activity is allowed, and the last element is
    # the time, in the same format, where the activity is no longer allowed.
    # Ex. ["charging", 1] -> (32400, 61200) means that on day 1, charging is allowed from 9AM to 5PM.
    time_ranges: Mapping[str, Mapping[int, Tuple[float, float]]]

    @property
    def duration(self) -> int:
        """
        Obtain the number of days that the competition encompasses
        """
        return len(self.time_ranges["driving"].keys())

    def route_hash(self):
        return hash(self.route)


class TrackCompetitionConfig(CompetitionConfig):
    tiling: int  # The number of times to tile the route to build the route

    def route_hash(self):
        return hash(hash(self.route_config) + hash(self.tiling))


class RoadCompetitionConfig(CompetitionConfig):
    """
    A model which contains the information required
    """
    pass

from simulation.config import Config, ConfigDict
from simulation.common import Coordinate
from pydantic import Field


class InitialConditions(Config):
    model_config = ConfigDict(frozen=True)

    current_coord: Coordinate                           # Initial Position of the car
    initial_battery_soc: float = Field(ge=0.0, le=1.0)  # 0% <= SOC < 100%
    start_time: int                                     # Time since the beginning of the first day (12:00:00AM) in s

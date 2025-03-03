from datetime import datetime
from typing import Tuple, Mapping, List, Dict
from strenum import StrEnum
from enum import Enum
from simulation.config import Config, ConfigDict, CompetitionConfig
from pydantic import BaseModel
from numpy.typing import NDArray


class SimulationReturnType(StrEnum):
    """

    This enum exists to discretize different data types run_model should return.

    """

    time_taken = "time_taken"
    distance_travelled = "distance_travelled"
    distance_and_time = "distance_and_time"
    void = "void"


class SimulationHyperparametersConfig(Config):
    model_config = ConfigDict(frozen=True)

    vehicle_speed_period: int           # The period that an element of the vehicle speed array will control, in s
    return_type: SimulationReturnType   # The kind of data that simulation will immediately return
    simulation_period: int              # The discrete temporal timestep of Simulation, in s


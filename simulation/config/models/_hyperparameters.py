from strenum import StrEnum
from simulation.config.models import Config, ConfigDict


class SimulationReturnType(StrEnum):
    """

    This enum exists to discretize different data types run_model should return.

    """

    time_taken = "time_taken"
    distance_travelled = "distance_travelled"
    distance_and_time = "distance_and_time"
    void = "void"


class SimulationHyperparametersConfig(Config):
    """
    Configuration object specifying the hyperparameters used by a simulation.
    """
    model_config = ConfigDict(frozen=True)

    speed_dt: (
        int  # The period that an element of the vehicle speed array will control, in s
    )
    return_type: (
        SimulationReturnType  # The kind of data that simulation will immediately return
    )
    simulation_period: int  # The discrete temporal timestep of Simulation, in s

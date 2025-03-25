from simulation.config.models import Config, ConfigDict
from pydantic import Field


class InitialConditions(Config):
    """
    Configuration object describing the initial conditions for a simulation.
    """
    model_config = ConfigDict(frozen=True)

    current_coord: tuple[float, float]  # Initial Position of the car
    initial_battery_soc: float = Field(ge=0.0, le=1.0)  # 0% <= SOC < 100%
    start_time: int  # Time since the beginning of the first day (12:00:00AM) in s

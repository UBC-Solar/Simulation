from pydantic import BaseModel, ConfigDict, Field


class MutableInitialConditions(BaseModel):
    """
    Pydantic object which stores user-adjustable initial condition parameters for simulation optimization runs
    """
    model_config = ConfigDict(extra="ignore")

    current_coord: tuple[float, float]  # Initial Position of the car
    initial_battery_soc: float = Field(ge=0.0, le=1.0)  # 0% <= SOC < 100%
    start_time: int  # Time since the beginning of the first day (12:00:00AM) in s

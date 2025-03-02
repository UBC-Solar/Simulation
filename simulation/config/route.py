from pydantic import BaseModel, ConfigDict


class Route(BaseModel):
    model_config = ConfigDict(frozen=True)

    speed_limits: list[float]
    path_elevations: list[float]
    path_time_zones: list[float]
    coords: list[float]
    tiling: int

from pydantic import BaseModel, ConfigDict
from numpy.typing import NDArray


class Route(BaseModel):
    """
    `Route` encapsulates all the information required to completed describe a physical route that we want
    to simulate.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    speed_limits: NDArray[float]
    tiling: int

    # NOTE: Subsequent arrays all should have the same length (that is, each have one element per coordinate)
    path_elevations: NDArray[float]
    path_time_zones: NDArray[float]
    coords: NDArray[float]

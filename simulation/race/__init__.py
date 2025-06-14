"""
The `race` module contains utilities and classes relating to the
manipulation of time-series data and localized data along a competition.
"""

from ._race import Race

from ._route import Route

from ._helpers import (
    reshape_speed_array,
    adjust_timestamps_to_local_times,
    get_array_directional_wind_speed,
    get_granularity_reduced_boolean,
    calculate_completion_index,
    get_map_data_indices,
    normalize,
    denormalize,
    rescale,
)

Coordinate = tuple[float, float]

__all__ = [
    "Race",
    "Route",
    "reshape_speed_array",
    "adjust_timestamps_to_local_times",
    "get_array_directional_wind_speed",
    "get_granularity_reduced_boolean",
    "calculate_completion_index",
    "get_map_data_indices",
    "normalize",
    "denormalize",
    "rescale",
    "Coordinate"
]

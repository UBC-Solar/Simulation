"""
This class collects the constants that are related to a specific competition.
"""

import numpy as np
from simulation.config import CompetitionConfig
from typing import Mapping

DAY_LENGTH: int = 24 * 60 * 60  # Length of a day in seconds


class Race:
    def __init__(self, config: CompetitionConfig):
        self.race_type = config.competition_type

        self.charging_times = config.time_ranges["charging"]
        self.driving_times = config.time_ranges["driving"]

        self.tiling = getattr(config, "tiling", 1)
        self.date = config.date

        self.race_duration = config.duration * DAY_LENGTH  # Duration (s)
        self.driving_boolean = self.make_time_boolean(self.driving_times)
        self.charging_boolean = self.make_time_boolean(self.charging_times)

    def __str__(self):
        return str(self.race_type)

    def make_time_boolean(self, time_range: Mapping[int, tuple[float, float]]):
        boolean: np.ndarray = np.empty(self.race_duration, dtype=np.int8)

        for tick in range(len(boolean)):
            day: int = (
                tick // DAY_LENGTH
            )  # Integer division to determine how many days have passed
            time_of_day = (
                tick % DAY_LENGTH
            )  # Time of day in seconds where 0 is midnight and 43200 is noon
            begin, end = time_range[day]

            # If the time of day is between the beginning and end, then the boolean is True, else False
            boolean[tick] = begin <= time_of_day < end

        return boolean

    def driving_windows(self, start_time: float = 0) -> list[tuple[int, float, float]]:
        """
        The race's driving hours as a list of `(day, start, end)`, in seconds since midnight on
        day 0. Windows that are over by `start_time` are dropped, and one that has already begun
        is trimmed to start there.

        Tick mode reads the same hours as a per-second yes/no array (`driving_boolean`). Lap mode
        needs them as windows, to tell whether a whole lap fits before driving stops.
        """
        windows = []
        for day, (begin, end) in sorted(self.driving_times.items()):
            window_start, window_end = day * DAY_LENGTH + begin, day * DAY_LENGTH + end
            if window_end > start_time:
                windows.append((day, max(window_start, start_time), window_end))
        return windows

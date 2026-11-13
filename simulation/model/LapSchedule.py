from typing import Optional

import numpy as np
from numpy.typing import NDArray

from simulation.model.LapGIS import LapGIS
from simulation.race import IDLE_TIME, Race

MIN_SEGMENT_SPEED_KMH = 1.0  # lap mode divides by speed, so no stretch may be 0 km/h


class LapSchedule:
    """
    When every lap of the race happens (timing only), from the one-lap track, the race's driving
    hours and one speed per lap. Lap mode's version of tick mode's `reshape_speed_array`.

    Rules: speeds are used in order, one per lap; 0 means wait `IDLE_TIME`; a lap that won't finish
    before driving stops for the day is tried again the next day. Results are arrays, one entry per
    lap (waits included).
    """

    def __init__(self, gis: LapGIS, race: Race, speeds_kmh, start_time: float = 0.0,
                 within_lap_kmh: Optional[NDArray[np.float64]] = None):
        """
        :param gis: one-lap track, `LapGIS.from_gis(model.gis)`.
        :param race: `model.race`, for its driving hours.
        :param start_time: seconds since midnight on day 0 (`model.start_time`).
        :param within_lap_kmh: optional km/h added to each stretch (the micro-strategy pattern).
        """
        num_points = len(gis.segment_lengths)
        if within_lap_kmh is None:
            within_lap_kmh = np.zeros(num_points)
        elif len(within_lap_kmh) != num_points:
            raise ValueError("within_lap_kmh needs one value per track point.")

        laps = []  # (day, start, duration, speed, segment_speeds, segment_times)
        plan_index = 0  # next entry of speeds_kmh to drive
        for day, window_start, window_end in race.driving_windows(start_time):
            clock = window_start
            while plan_index < len(speeds_kmh):
                speed_kmh = float(speeds_kmh[plan_index])
                segment_speeds, segment_times, duration = self._lap_timing(gis, speed_kmh, within_lap_kmh)

                if clock + duration > window_end:
                    break  # doesn't fit today: same plan entry, next day

                laps.append((day, clock, duration, speed_kmh, segment_speeds, segment_times))
                clock += duration
                plan_index += 1

        day, start, duration, speed, segment_speeds, segment_times = zip(*laps) if laps else [()] * 6
        self.lap_length_m = gis.path_length
        self.day = np.array(day, dtype=int)  # race day (starting from 0)
        self.start = np.array(start, dtype=float)  # start time in seconds since midnight day 0
        self.duration = np.array(duration, dtype=float)  # seconds
        self.end = self.start + self.duration  # end time in seconds since midnight day 0
        self.speed_kmh = np.array(speed, dtype=float)  # the plan's speed for this lap; 0 or less means it's a wait
        self.is_wait = self.speed_kmh <= 0
        # one row per lap, one column per stretch (LapGIS convention); all zeros for a wait
        self.segment_speeds = np.array(segment_speeds, dtype=float).reshape(len(laps), num_points)  # m/s per stretch
        self.segment_times = np.array(segment_times, dtype=float).reshape(len(laps), num_points)  # seconds per stretch

    @staticmethod
    def _lap_timing(gis: LapGIS, speed_kmh: float, within_lap_kmh: NDArray[np.float64]):
        """Speed (m/s) and time (s) on each stretch of one lap, and the lap's total time. A speed of 0 is a wait."""
        if speed_kmh <= 0:
            zeros = np.zeros(len(gis.segment_lengths))
            return zeros, zeros, float(IDLE_TIME)
        segment_speeds = np.maximum(speed_kmh + within_lap_kmh, MIN_SEGMENT_SPEED_KMH) / 3.6
        segment_times = gis.segment_lengths / segment_speeds
        return segment_speeds, segment_times, float(segment_times.sum())

    def position_at(self, times) -> NDArray[np.float64]:
        """Metres driven by each of `times` (seconds since midnight on day 0): steady within a lap, still between laps."""
        times = np.asarray(times, dtype=float)
        driving = ~self.is_wait
        if not driving.any():
            return np.zeros_like(times)
        starts, ends = self.start[driving], self.end[driving]
        laps_done = np.arange(len(starts))
        knot_times = np.column_stack([starts, ends]).ravel()
        knot_laps = np.column_stack([laps_done, laps_done + 1]).ravel()
        return np.interp(times, knot_times, knot_laps * self.lap_length_m, left=0.0)

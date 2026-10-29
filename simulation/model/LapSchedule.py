from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from numpy.typing import NDArray

from simulation.model.LapProfile import LapProfile
from simulation.race import IDLE_TIME

# Lap mode divides by speed, so no stretch may be 0 km/h. Tick mode clips to 0 instead (it never
# divides by speed), so this floor is lap mode's version of that.
MIN_SEGMENT_SPEED_KMH = 1.0


@dataclass(frozen=True)
class ScheduledLap:
    """
    When one lap (or one wait) happens, and how fast the car goes on each stretch of it.

    The schedule produces these and the energy step reads them, so the timing is worked out once
    and can be checked on its own. Times are seconds since midnight on day 0. Per-stretch arrays
    follow `LapProfile`'s convention and are all zeros for a wait.
    """

    plan_index: int  # which entry of the speed plan this came from
    day: int # race day (starting from 0)
    start: float # start time in seconds since midnight day 0
    end: float # end time in seconds since midnight day 0
    speed_kmh: float  # the plan's speed for this lap; 0 or less means it's a wait
    segment_speeds: NDArray[np.float64]  # m/s per stretch
    segment_times: NDArray[np.float64]  # seconds per stretch

    @property
    def is_wait(self) -> bool:
        return self.speed_kmh <= 0

    @property
    def duration(self) -> float:
        return self.end - self.start


def schedule_laps(
    profile: LapProfile,
    speeds_kmh: Sequence[float],
    windows: list[tuple[int, float, float]],
    within_lap_kmh: Optional[NDArray[np.float64]] = None,
) -> list[ScheduledLap]:
    """
    Work out when each lap starts and ends. Timing only, no energy or battery.

    Lap mode's version of what tick mode does in `reshape_speed_array`, but the result is a list
    of laps instead of a speed for every tick.

    Rules:
      - `speeds_kmh` has one speed per lap, used in order. Leftover entries are ignored.
      - Each lap is driven at its planned speed, plus `within_lap_kmh` on each stretch if given.
      - A speed of 0 means wait `IDLE_TIME` seconds. It uses up one plan entry, like tick mode.
      - A lap that wouldn't finish before the window closes isn't started. The same plan entry is
        tried again when the next window opens. FSGP only counts finished laps.

    :param windows: driving hours as `(day, start, end)`, from `Race.driving_windows`.
    :param within_lap_kmh: optional km/h added to each stretch (the micro-strategy pattern).
    """
    num_points = len(profile.segment_lengths)
    if within_lap_kmh is None:
        within_lap_kmh = np.zeros(num_points)
    elif len(within_lap_kmh) != num_points:
        raise ValueError("within_lap_kmh needs one value per track point.")

    laps: list[ScheduledLap] = []
    plan_index = 0

    for day, window_start, window_end in windows:
        clock = window_startb

        while True:
            if plan_index >= len(speeds_kmh):
                return laps  # plan has run out
            speed_kmh = float(speeds_kmh[plan_index])

            if speed_kmh <= 0:
                segment_speeds = np.zeros(num_points)
                segment_times = np.zeros(num_points)
                duration = IDLE_TIME
            else:
                segment_kmh = np.maximum(speed_kmh + within_lap_kmh, MIN_SEGMENT_SPEED_KMH)
                segment_speeds = segment_kmh / 3.6
                segment_times = profile.segment_lengths / segment_speeds
                duration = float(segment_times.sum())

            if clock + duration > window_end:
                break  # doesn't fit today: same plan entry, next window

            laps.append(ScheduledLap(plan_index, day, clock, clock + duration, speed_kmh,
                                     segment_speeds, segment_times))
            clock += duration
            plan_index += 1

    return laps

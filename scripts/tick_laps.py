import numpy as np
import pandas as pd

from simulation.race import DAY_LENGTH


def laps_from_ticks(start_times, speed_kmh, distance_km, lap_length_km, dt) -> pd.DataFrame:
    """
    Cut tick-mode timing into laps, one row per lap, so it can be compared with lap mode. Used by
    `scripts/compare_schedules.py`.

    How laps are found: by distance. Each tick goes to the lap it started in, using the distance
    driven before that tick, divided by the lap length. Tick mode's own track point (which of the
    289 points the car is at) isn't used, because it moves 3.6x too fast (see `logs/bugs.md`).

    Only ticks where the car is moving count towards a lap. Time parked (nights, waits) belongs to
    no lap.

    Lap edges are rounded to whole ticks: a tick that crosses the line counts for the lap it started
    in. So a lap's `moving_time` can be off by up to one tick; the next lap gets the difference back.

    Columns: `lap`, `day`, `start` and `end` (seconds since midnight on day 0, like `LapSchedule`),
    `moving_time` (s), `complete` (did the total distance reach the end of this lap), and
    `crosses_night` (started one day, ended the next: tick mode carries an unfinished lap over to
    the next morning).

    :param start_times: when each tick starts, in seconds since midnight on day 0.
    :param speed_kmh: speed during each tick.
    :param distance_km: distance driven during each tick.
    :param lap_length_km: length of one lap.
    :param dt: tick length in seconds.
    """
    total_km = np.cumsum(distance_km)
    distance_before_km = total_km - distance_km
    moving = (speed_kmh > 0) & (distance_km > 0)

    ticks = pd.DataFrame({
        "lap": np.floor(distance_before_km / lap_length_km).astype(int)[moving],
        "start": np.asarray(start_times)[moving],
    })
    laps = ticks.groupby("lap").agg(start=("start", "first"), end=("start", "last"),
                                    moving_ticks=("start", "size")).reset_index()

    laps["end"] += dt  # the last tick runs for one more tick length
    laps["moving_time"] = laps.pop("moving_ticks") * dt
    laps["day"] = (laps["start"] // DAY_LENGTH).astype(int)
    laps["complete"] = (laps["lap"] + 1) * lap_length_km <= (total_km[-1] if len(total_km) else 0.0)
    laps["crosses_night"] = (laps["end"] // DAY_LENGTH).astype(int) != laps["day"]
    return laps

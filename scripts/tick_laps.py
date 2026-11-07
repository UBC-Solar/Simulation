import numpy as np
import pandas as pd

from simulation.race import DAY_LENGTH


def laps_from_ticks(start_times, speed_kmh, distance_km, lap_length_km, dt) -> pd.DataFrame:
    """
    Cut tick-mode timing into laps, to compare with lap mode. Laps are found by distance (tick mode's
    track point moves 3.6x too fast); only moving ticks count; a tick that crosses the line counts
    for the lap it started in.

    Columns: `lap`, `day`, `start`, `end` (s since midnight day 0), `moving_time` (s), `complete`
    (reached the end of the lap), `crosses_night` (tick mode carries an unfinished lap overnight).
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

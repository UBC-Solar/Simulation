import numpy as np
import pandas as pd

from simulation.race import DAY_LENGTH


def tick_results_per_lap(model) -> pd.DataFrame:
    """
    Cut a finished tick-mode run into laps, one row per lap, so it can be compared with lap mode.

    Tick mode's results are one value every tick for the whole race, with nothing saying where a lap
    starts or ends. This works the laps out afterwards and adds up each one. It only reads the
    results; tick mode itself is unchanged.

    The run is cut where the battery first drops below 0, like tick mode's own distance. How the
    laps are found is explained in `laps_from_ticks`.

    Columns: those of `laps_from_ticks`, plus `motor_energy`, `electronics_energy`, `solar_energy`,
    `regen_energy` (all J, while moving), and `battery_end` and `battery_min` (0 to 1).

    :param model: a `Model` after `run_model` has been called.
    """
    (timestamps, speed_kmh, distance_km, battery, motor, consumed, solar, regen) = model.get_results([
        "timestamps", "speed_kmh", "distance", "state_of_charge", "motor_consumed_energy",
        "consumed_energy", "array_produced_energy", "regen_produced_energy",
    ])

    # Cut at the first tick where the battery is below 0 (or keep everything if it never is)
    dead = np.flatnonzero(battery < 0)
    end = dead[0] if len(dead) else len(timestamps)

    return laps_from_ticks(
        start_times=model.start_time + timestamps[:end],
        speed_kmh=speed_kmh[:end],
        distance_km=distance_km[:end],
        lap_length_km=model.gis.path_length / 1000,
        dt=model.simulation_dt,
        extra={
            "motor_energy": (motor[:end], "sum"),
            "electronics_energy": ((consumed - motor)[:end], "sum"),
            "solar_energy": (solar[:end], "sum"),
            "regen_energy": (regen[:end], "sum"),
            "battery_end": (battery[:end], "last"),
            "battery_min": (battery[:end], "min"),
        },
    )


def laps_from_ticks(start_times, speed_kmh, distance_km, lap_length_km, dt, extra=None) -> pd.DataFrame:
    """
    Group per-tick values into laps. Used by `tick_results_per_lap`, and by the schedule comparison
    (`scripts/compare_schedules.py`), which has tick-mode timing but no physics.

    How laps are found: by distance. Each tick goes to the lap it started in, using the distance
    driven before that tick, divided by the lap length. Tick mode's own track point (which of the
    289 points the car is at) isn't used, because it moves 3.6x too fast (see `logs/bugs.md`).

    Only ticks where the car is moving count towards a lap. Time parked (nights, waits) belongs to
    no lap.

    Lap edges are rounded to whole ticks: a tick that crosses the line counts for the lap it started
    in. So a lap's `distance` and `moving_time` can be off by up to one tick (about 2% at 10 s ticks);
    the next lap gets the difference back.

    Columns: `lap`, `day`, `start` and `end` (seconds since midnight on day 0, like `ScheduledLap`),
    `moving_time` (s), `distance` (m), `avg_speed_kmh`, `complete` (did the total distance reach the
    end of this lap), `crosses_night` (started one day, ended the next: tick mode carries an
    unfinished lap over to the next morning), then one column per entry in `extra`.

    :param start_times: when each tick starts, in seconds since midnight on day 0.
    :param speed_kmh: speed during each tick.
    :param distance_km: distance driven during each tick.
    :param lap_length_km: length of one lap.
    :param dt: tick length in seconds.
    :param extra: more per-tick values to add up per lap, as `{column: (values, how)}`, where `how` is
        a pandas aggregation such as `"sum"`, `"last"` or `"min"`.
    """
    extra = extra or {}
    total_km = np.cumsum(distance_km)
    distance_before_km = total_km - distance_km
    moving = (speed_kmh > 0) & (distance_km > 0)

    ticks = pd.DataFrame({
        "lap": np.floor(distance_before_km / lap_length_km).astype(int)[moving],
        "start": np.asarray(start_times)[moving],
        "distance": distance_km[moving] * 1000,
        **{column: np.asarray(values)[moving] for column, (values, _) in extra.items()},
    })

    laps = ticks.groupby("lap").agg(
        start=("start", "first"),
        end=("start", "last"),
        moving_ticks=("start", "size"),
        distance=("distance", "sum"),
        **{column: (column, how) for column, (_, how) in extra.items()},
    ).reset_index()

    laps["end"] += dt  # the last tick runs for one more tick length
    laps["moving_time"] = laps.pop("moving_ticks") * dt
    laps["avg_speed_kmh"] = laps["distance"] / laps["moving_time"] * 3.6
    laps["day"] = (laps["start"] // DAY_LENGTH).astype(int)
    distance_at_end_km = total_km[-1] if len(total_km) else 0.0
    laps["complete"] = (laps["lap"] + 1) * lap_length_km <= distance_at_end_km
    laps["crosses_night"] = (laps["end"] // DAY_LENGTH).astype(int) != laps["day"]

    return laps[["lap", "day", "start", "end", "moving_time", "distance", "avg_speed_kmh",
                 "complete", "crosses_night", *extra]]

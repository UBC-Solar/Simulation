"""
Check that lap mode's timing matches tick mode's: same model, same speeds, same micro-strategy.
Timing only, no energy or battery. Prints one table per test.

Run from the repo root: `.venv/bin/python -m scripts.compare_schedules --wsl-cache`
(`--wsl-cache` only while the route cache has Windows-style keys; see `logs/bugs.md`).
"""

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np

from micro_strategy import OptimizedSpeedsPath
from simulation.cmd.run_simulation import build_model, get_default_settings
from simulation.config import SimulationHyperparametersConfig, SimulationReturnType, WeatherProvider
from simulation.model import LapGIS, LapSchedule
from simulation.race import DAY_LENGTH
from simulation.race._helpers import LAPS_PER_INDEX

NUM_BLOCKS = 30  # tick mode takes one speed per 10 laps; 30 is more than any race needs
LAPS_TOLERANCE = 1  # tick mode finishes the lap it carried over from the night before; lap mode never starts one
DRIFT_TOLERANCE_LAPS = 0.1  # how far apart the two cars may drift during one day

# The micro-strategy is the file in `micro_strategy/optimization_results/`: 289 small km/h changes, one
# per track point, added to the lap's speed so the car speeds up and slows down around each lap.

# (name, note printed under it, km/h per 10 laps (repeated), micro-strategy on, days to check; None = every day)
TESTS = [
    ("Steady 30 km/h, with micro-strategy",
     "Checks every day. Tests that both modes apply the micro-strategy the same way.",
     [30.0], True, None),
    ("Speed changes every 10 laps (28, 34, 40, 31 km/h), without micro-strategy",
     "Tests that both modes change speed at the same lap. Checks day 0 only: at the end of each day\n"
     "  tick mode drops the rest of its 10-lap block and lap mode doesn't, so from day 1 they drive\n"
     "  different speeds. Micro-strategy off: with it, tick mode changes speed a little before lap 10,\n"
     "  20, 30 (a tick-mode bug in logs/bugs.md).",
     [28.0, 34.0, 40.0, 31.0], False, [0]),
]


def flat_forecast(model):
    """Made-up steady weather over the whole race. Tick mode needs some to run; its timing doesn't use it."""
    start = model.time_of_initialization - DAY_LENGTH  # a day either side, so local-time lookups stay inside
    times = np.arange(start, model.time_of_initialization + model.simulation_duration + DAY_LENGTH, 300)
    forecast = np.zeros((1, len(times), 6))
    forecast[0, :, 0] = times
    forecast[0, :, 1:3] = model.gis.launch_point
    forecast[0, :, 5] = 500.0  # sunlight, W/m²
    return forecast, WeatherProvider.Solcast


def set_micro_strategy(on):
    """
    Turn the micro-strategy on or off in both modes, and return it as lap mode takes it (km/h per
    stretch). Tick mode always loads the file (`Model.run_model`), so "off" points it at zeros.
    """
    raw = np.load(OptimizedSpeedsPath)
    path = OptimizedSpeedsPath
    if not on:
        path = Path(tempfile.gettempdir()) / "no_micro_strategy.npy"
        np.save(path, np.zeros_like(raw))
    sys.modules["simulation.model.Model"].OptimizedSpeedsPath = path
    return (raw - raw.mean()) / 2 if on else np.zeros_like(raw)  # scaled the way tick mode does (Simulation.py)


def compare(model, lap_gis, block_speeds, micro_strategy, days):
    """Rows of (measure, tick mode, lap mode, ok) for one test."""
    blocks = np.resize(block_speeds, NUM_BLOCKS)
    lap_km = lap_gis.path_length / 1000
    micro_strategy_kmh = set_micro_strategy(micro_strategy)

    # Tick mode: a real run. Laps are found by distance: a lap ends where the running total reaches
    # the next multiple of the lap length.
    model.run_model(speed=blocks, weather=flat_forecast(model), is_optimizer=True)
    timestamps, tick_km = model.get_results(["timestamps", "distance"])
    times = model.start_time + timestamps  # seconds since midnight on day 0, like lap mode
    total_km = np.cumsum(tick_km)
    lap_ends = np.searchsorted(total_km, np.arange(1, int(total_km[-1] // lap_km) + 1) * lap_km)
    tick_lap_days = times[lap_ends] // DAY_LENGTH

    # Lap mode: the same speeds, one per lap
    schedule = LapSchedule(lap_gis, model.race, np.repeat(blocks, LAPS_PER_INDEX), model.start_time, micro_strategy_kmh)
    gap_m = total_km * 1000 - schedule.position_at(times)  # how far tick mode's car is ahead

    rows = []
    for day, start, _ in model.race.driving_windows(model.start_time):
        if days is not None and day not in days:
            continue
        laps = ~schedule.is_wait & (schedule.day == day)
        tick_laps, lap_laps = int((tick_lap_days == day).sum()), int(laps.sum())
        rows.append((f"Laps finished on day {day}", tick_laps, lap_laps, abs(tick_laps - lap_laps) <= LAPS_TOLERANCE))

        # Drift: how much the gap changes during the day, up to lap mode's last lap. The gap at the
        # start of the day is tick mode's unfinished lap from the night before, so it's taken off.
        day_gap = gap_m[(times >= start) & (times <= schedule.end[laps].max())]
        drift_m = float(np.max(np.abs(day_gap - day_gap[0])))
        rows.append((f"Drift on day {day}", f"{drift_m:.0f} m", "", drift_m <= DRIFT_TOLERANCE_LAPS * lap_km * 1000))
    return rows


def use_windows_cache_keys(tiling):
    """Read the Windows-written route cache on WSL (read-only). Remove once the cache bug is fixed."""
    import copy
    import pickle

    from simulation.cache._fs_cache import DillShelf, FSCache
    from simulation.race import Route

    original_get = FSCache.get

    def get(self, file_path):
        try:
            value = original_get(self, file_path)
        except KeyError:
            with DillShelf(self._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL) as db:
                value = db[str(file_path).replace("/", "\\")]
        if isinstance(value, Route) and value.tiling != tiling:
            value = copy.copy(value)
            object.__setattr__(value, "tiling", tiling)
        return value

    FSCache.get = get
    FSCache.put = lambda self, obj, file_path: None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--wsl-cache", action="store_true",
                        help="Read the Windows-written route cache on WSL/Linux (read-only).")
    args = parser.parse_args()

    initial_conditions, environment, car = get_default_settings("FSGP", "Brightside")
    if args.wsl_cache:
        use_windows_cache_keys(environment.competition_config.tiling)

    hyperparameters = SimulationHyperparametersConfig.build_from({
        "simulation_period": 10,  # the normal tick length
        "return_type": SimulationReturnType.distance_and_time,
        "speed_dt": 1,
    })
    model = build_model(environment, hyperparameters, initial_conditions, car)
    lap_gis = LapGIS.from_gis(model.gis)

    for name, note, block_speeds, micro_strategy, days in TESTS:
        print(f"\n{name}\n  {note}")
        print(f"  {'Measure':<26}{'Tick mode':>12}{'Lap mode':>12}")
        for measure, tick, lap, ok in compare(model, lap_gis, block_speeds, micro_strategy, days):
            print(f"  {measure:<26}{tick:>12}{lap:>12}  {'ok' if ok else 'CHECK'}")


if __name__ == "__main__":
    main()

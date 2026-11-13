"""
Show what's in the simulation cache: every saved route, race and forecast, plus the other files in the cache folder.

Read only. Nothing is changed or downloaded.
"""
import pickle
from datetime import datetime, timezone

from simulation.cache import SimulationCache
from simulation.cache._fs_cache import DillShelf


def describe(value) -> str:
    """A one-line summary of a cached route, race or forecast."""
    kind = type(value).__name__
    if kind == "Route":
        return f"Route: {len(value.coords)} track points, labelled {value.tiling} copies"
    if kind == "Race":
        days = value.race_duration // 86400
        return f"Race: starts {value.date:%Y-%m-%d %H:%M}, {days} days, labelled {value.tiling} copies"

    saved = ""
    if isinstance(value, tuple):  # Forecasts saved since task 1 are (forecast, when it was fetched)
        value, fetched_at = value
        saved = f", saved {fetched_at:%Y-%m-%d}"
    if getattr(value, "ndim", 0) == 3:
        if value.shape[2] != 6:  # Solcast forecasts are [1 coordinate][times][6]
            return f"Forecast array {value.shape}, not Solcast's layout (old Openweather?){saved}"
        times = value[0, :, 0]
        start, end = (datetime.fromtimestamp(float(t), timezone.utc) for t in (times.min(), times.max()))
        return f"Forecast {value.shape}: {start:%Y-%m-%d} to {end:%Y-%m-%d}{saved}"

    return kind


def main():
    folder = SimulationCache._shelve_dir.parent

    print(f"Entries in {SimulationCache._shelve_dir.relative_to(folder.parent.parent)}.*\n")
    with DillShelf(SimulationCache._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL, flag="r") as db:
        for key in sorted(db.keys()):
            size_kb = len(db.dict[key.encode()]) / 1024
            print(f"  {key:28} {size_kb:8.0f} KB  {describe(db[key])}")

    print("\nFiles in the cache folder\n")
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix not in (".py", ".pyc"):
            print(f"  {str(path.relative_to(folder)):45} {path.stat().st_size / 1024:8.0f} KB")


if __name__ == "__main__":
    main()

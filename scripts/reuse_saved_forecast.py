"""
Re-save an old cached forecast under the weather key the code uses now, so the entry points find it.

Forecasts saved before task 1 sit under `weather/<config hash>` (or `weather\\<config hash>` on
Windows) as a bare array. `fetch_competition_weather` now looks under a digest of the query, and
expects `(forecast, fetched_at)`. This finds an old Solcast forecast that covers the race dates in
`settings_<race>.toml` and copies it to the new key. Nothing is downloaded.
"""
import argparse
import pickle
from datetime import datetime, timedelta, timezone

from simulation.cache import SimulationCache
from simulation.cache._fs_cache import DillShelf
from simulation.cmd.run_simulation import get_default_settings
from simulation.query._weather import (
    DEFAULT_SOLCAST_PERIOD,
    WeatherProvider,
    _weather_cache_key,
)


def find_old_forecast(db, start_utc, end_utc):
    """An old Solcast forecast whose times cover `start_utc` to `end_utc`, or `None`."""
    for key in db.keys():
        if not key.startswith(("weather/", "weather\\")):
            continue
        forecast = db[key]
        # Solcast forecasts are [1 coordinate][times][6]: time, lat, lon, wind speed, wind dir, sunlight.
        if not hasattr(forecast, "shape") or forecast.ndim != 3 or forecast.shape[2] != 6:
            continue
        times = forecast[0, :, 0]
        # Saved times are local, shifted by up to a day from UTC either way.
        if times.min() <= start_utc + 86400 and times.max() >= end_utc - 86400 \
                and times.max() - times.min() >= end_utc - start_utc:
            return key, forecast
    return None, None


def main(race: str):
    _, environment, _ = get_default_settings(race)
    competition = environment.competition_config
    start = competition.date
    end = start + timedelta(days=competition.duration)

    new_key = _weather_cache_key(
        WeatherProvider.Solcast, competition.route_config.coordinates, DEFAULT_SOLCAST_PERIOD,
        start, end, competition.competition_type,
    )

    with DillShelf(SimulationCache._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL) as db:
        old_key, forecast = find_old_forecast(db, start.timestamp(), end.timestamp())

    if forecast is None:
        raise SystemExit(f"No saved Solcast forecast covers {start} to {end}.")

    # The real fetch time wasn't saved with old forecasts, so record when it was copied.
    SimulationCache.put((forecast, datetime.now(timezone.utc)), new_key)
    print(f"Copied {old_key!r} -> {new_key.as_posix()!r} ({start:%Y-%m-%d} to {end:%Y-%m-%d})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--race", default="FSGP")
    main(parser.parse_args().race)

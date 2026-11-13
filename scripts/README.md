# scripts

Testing and checking tools for the simulation. **Not part of the simulation package:**
`pyproject.toml` only ships `simulation` and `micro_strategy`, and nothing in `simulation/` imports
from here.

Run them from the repo root, as modules:

| Script | What it does | Run |
| --- | --- | --- |
| `compare_schedules.py` | Runs tick mode's and lap mode's timing over the full race with the same speeds, and writes a comparison report (`logs/lap_mode/schedule_comparison.html`). | `.venv/bin/python -m scripts.compare_schedules` |
| `tick_laps.py` | Cuts tick mode's per-tick timing into laps, so it can be compared with lap mode. Used by `compare_schedules.py`. | imported, not run |
| `show_cache.py` | Lists every saved route, race and forecast in the cache (what it is, size, dates), plus the other files in `simulation/cache/`. Read only. | `.venv/bin/python -m scripts.show_cache` |
| `reuse_saved_forecast.py` | Copies an old cached forecast that covers the race dates in `settings_<race>.toml` to the weather key the code uses now. Run it after changing the race date. | `.venv/bin/python -m scripts.reuse_saved_forecast` |

`--wsl-cache` isn't needed any more: the cache reads Windows-style keys on every system now.

# scripts

Testing and checking tools for the simulation. **Not part of the simulation package:**
`pyproject.toml` only ships `simulation` and `micro_strategy`, and nothing in `simulation/` imports
from here.

Run them from the repo root, as modules:

| Script | What it does | Run |
| --- | --- | --- |
| `compare_schedules.py` | Runs tick mode and lap mode with the same speeds and prints, per day, how many laps each finished and how far apart the two cars drift. Timing only. | `.venv/bin/python -m scripts.compare_schedules --wsl-cache` |
| `show_cache.py` | Lists every saved route, race and forecast in the cache (what it is, size, dates), plus the other files in `simulation/cache/`. Read only. | `.venv/bin/python -m scripts.show_cache` |
| `reuse_saved_forecast.py` | Copies an old cached forecast that covers the race dates in `settings_<race>.toml` to the weather key the code uses now. Run it after changing the race date. | `.venv/bin/python -m scripts.reuse_saved_forecast` |

`--wsl-cache` lets `compare_schedules` use the saved route without a Google Maps key. The cache reads
Windows-style keys everywhere now, but the saved route was built with a different `tiling` than the
config, which makes the build try to download it again. The flag works around that and never writes
to the cache.
# scripts

Testing and checking tools for the simulation. **Not part of the simulation package:**
`pyproject.toml` only ships `simulation` and `micro_strategy`, and nothing in `simulation/` imports
from here.

Run them from the repo root, as modules:

| Script | What it does | Run |
| --- | --- | --- |
| `compare_schedules.py` | Runs tick mode and lap mode with the same speeds and prints, per day, how many laps each finished and how far apart the two cars drift. Timing only. | `.venv/bin/python -m scripts.compare_schedules --wsl-cache` |

`--wsl-cache` lets it use the saved route without a Google Maps key. The saved route has Windows-style
keys (a problem on Mac and Linux) and was built with a different `tiling` than the config, which
makes the build try to download it again. The flag works around both and never writes to the cache.

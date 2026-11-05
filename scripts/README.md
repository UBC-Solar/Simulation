# scripts

Testing and checking tools for the simulation. **Not part of the simulation package:**
`pyproject.toml` only ships `simulation` and `micro_strategy`, and nothing in `simulation/` imports
from here.

Run them from the repo root, as modules:

| Script | What it does | Run |
| --- | --- | --- |
| `compare_schedules.py` | Runs tick mode's and lap mode's timing over the full race with the same speeds, and writes a comparison report (`logs/lap_mode/schedule_comparison.html`). | `.venv/bin/python -m scripts.compare_schedules --wsl-cache` |
| `tick_laps.py` | Cuts a tick-mode run into laps, so it can be compared with lap mode. Used by `compare_schedules.py`. | imported, not run |

`--wsl-cache` is only needed on WSL/Linux while the route cache has Windows-style keys (see
`logs/bugs.md`).

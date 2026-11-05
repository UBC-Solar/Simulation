"""
Compare tick mode's schedule with lap mode's schedule over the full race. Timing only, no physics.

Both modes get the same model (car, track, race hours), the same speeds and the same within-lap
pattern. The script then checks that they drive the same laps at the same times: laps per day,
distance per day, lap times, and how far apart the two cars are at every moment of the race.

Output: a summary table in the terminal, and an HTML report with charts. The top of the report
records exactly what was run (git commit, uncommitted changes, command, settings).

Run from the repo root:

    .venv/bin/python -m scripts.compare_schedules --wsl-cache

`--wsl-cache` is only needed on WSL/Linux while the route cache has Windows-style keys (see
`logs/bugs.md`). It reads the cache, never writes it.

Tick mode's timing is reproduced here line for line from `Model.run_model` and
`Simulation.run_simulation_calculations` (speed plan → speed every tick → track position → distance),
without the weather and energy steps. So it covers the whole race and doesn't stop when the battery
would run out. `--check-against-run-model` confirms the copy matches a real `run_model`.
"""

import argparse
import datetime
import html
import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from micro_strategy import OptimizedSpeedsPath
from simulation.cmd.run_simulation import build_model, get_default_settings
from simulation.config import SimulationHyperparametersConfig, SimulationReturnType
from simulation.model import LapGIS, schedule_laps
from scripts.tick_laps import laps_from_ticks
from simulation.race import DAY_LENGTH, reshape_speed_array
from simulation.race._helpers import LAPS_PER_INDEX

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "logs" / "lap_mode" / "schedule_comparison.html"
NUM_BLOCKS = 30  # tick-mode plan length: 30 values x 10 laps, more than any race needs

# Tolerances for the ✅ / ⚠️ marks
LAP_TIME_TOLERANCE = 0.01  # 1% difference in average lap time
LAPS_PER_DAY_TOLERANCE = 1  # laps
DISTANCE_PER_DAY_TOLERANCE_LAPS = 1.0  # tick mode may drive one unfinished lap at day end
DRIFT_TOLERANCE_LAPS = 0.1  # how far the cars may drift apart within one day


@dataclass
class Scenario:
    name: str
    block_speeds: list  # km/h, one per 10 laps (tick mode's format); lap mode repeats each 10 times
    tick: int  # seconds
    pattern: bool  # add the micro-strategy within-lap pattern in both modes
    why: str = ""  # what this scenario shows, and what to expect


DEFAULT_SCENARIOS = [
    Scenario("Steady 30 km/h, no pattern, 1 s ticks", [30.0], 1, False,
             "The simplest case. Expect a match, apart from the day-end rule."),
    Scenario("Steady 30 km/h, with pattern, 1 s ticks", [30.0], 1, True,
             "Adds the within-lap pattern. At 1 s ticks tick mode reads it in nearly the right place, "
             "so expect a match."),
    Scenario("Steady 30 km/h, with pattern, 10 s ticks (today's default)", [30.0], 10, True,
             "Expected to fail. Tick mode's track position moves 3.6x too fast (logs/bugs.md), so at "
             "10 s ticks it reads the pattern at the wrong points, and its laps come out about 2.6% "
             "quicker. This is the bug showing, not lap mode."),
    Scenario("Changing speeds every 10 laps, with pattern, 1 s ticks", [28.0, 34.0, 40.0, 31.0], 1, True,
             "Expected to drift after day 0. When driving stops mid-block, tick mode drops the rest of "
             "that 10-lap block and starts the next speed in the morning; lap mode carries on with the "
             "same plan. So from day 1 the two drive different speeds on some laps."),
]


# ----- Running both modes -----

def tick_mode_timing(model, block_speeds, pattern_kmh):
    """
    Tick mode's timing steps, copied from `Model.run_model` and `Simulation.run_simulation_calculations`
    with nothing else. Returns per-tick start times (seconds since midnight on day 0), speeds (km/h)
    and distances (km).
    """
    dt = model.simulation_dt
    speed_kmh = reshape_speed_array(model.race, block_speeds, model.start_time, model.gis, dt,
                                    model.max_acceleration, model.max_deceleration)
    timestamps = np.arange(0, model.simulation_duration, dt)
    _, speed_kmh = model.gis.calculate_speeds_and_position(
        np.asarray(speed_kmh, dtype=np.float64), np.asarray(pattern_kmh, dtype=np.float64), dt)
    speed_kmh = np.clip(np.asarray(speed_kmh), a_min=0.0, a_max=None)
    tick_array = np.full_like(timestamps, fill_value=dt, dtype="f4")
    tick_array[0] = 0
    time_in_motion = np.logical_and(tick_array, speed_kmh) * dt
    distance_km = speed_kmh * (time_in_motion / 3600)
    return model.start_time + timestamps, speed_kmh, distance_km


def run_scenario(model, lap_gis, scenario, pattern_kmh):
    blocks = list(np.resize(scenario.block_speeds, NUM_BLOCKS))
    pattern = pattern_kmh if scenario.pattern else np.zeros(len(lap_gis.segment_lengths))
    lap_length_km = lap_gis.path_length / 1000

    # Tick mode: per-tick timing, cut into laps
    tick_times, tick_speed, tick_distance = tick_mode_timing(model, blocks, pattern)
    tick_laps = laps_from_ticks(tick_times, tick_speed, tick_distance, lap_length_km, model.simulation_dt)

    # Lap mode: the same speeds, one per lap
    lap_speeds = np.repeat(blocks, LAPS_PER_INDEX)
    windows = model.race.driving_windows(model.start_time)
    scheduled = [lap for lap in schedule_laps(lap_gis, lap_speeds, windows, pattern) if not lap.is_wait]
    lap_laps = pd.DataFrame({"lap": range(len(scheduled)), "day": [lap.day for lap in scheduled],
                             "start": [lap.start for lap in scheduled], "end": [lap.end for lap in scheduled],
                             "duration": [lap.duration for lap in scheduled]})

    # Where each car is at every tick: tick mode's running distance, lap mode's laps interpolated
    tick_position_m = np.cumsum(tick_distance) * 1000
    knot_times = np.ravel(np.column_stack([lap_laps["start"], lap_laps["end"]]))
    knot_positions = np.ravel(np.column_stack([np.arange(len(lap_laps)), np.arange(1, len(lap_laps) + 1)]))
    lap_position_m = np.interp(tick_times, knot_times, knot_positions * lap_gis.path_length,
                               left=0.0) if len(lap_laps) else np.zeros_like(tick_times)

    return {
        "scenario": scenario,
        "tick_laps": tick_laps,
        "lap_laps": lap_laps,
        "tick_times": tick_times,
        "tick_distance_km": tick_distance,
        "gap_m": tick_position_m - lap_position_m,
        "windows": windows,
        "lap_length_km": lap_length_km,
    }


def summarise(result):
    """Rows of (measure, tick mode, lap mode, difference, ok, note) for one scenario."""
    tick_laps, lap_laps = result["tick_laps"], result["lap_laps"]
    lap_km = result["lap_length_km"]
    tick_day = (result["tick_times"] // DAY_LENGTH).astype(int)
    rows = []

    tick_same_day = tick_laps[tick_laps["complete"] & ~tick_laps["crosses_night"]]
    t_mean, l_mean = tick_same_day["moving_time"].mean(), lap_laps["duration"].mean()
    diff = (t_mean - l_mean) / l_mean
    rows.append(("Average lap time", f"{t_mean:.1f} s", f"{l_mean:.1f} s", f"{diff:+.2%}",
                 abs(diff) <= LAP_TIME_TOLERANCE, "Tick mode: complete laps that don't cross a night."))

    for day, _, _ in result["windows"]:
        t_done = int(((tick_laps["complete"]) & (((tick_laps["end"] - 1e-6) // DAY_LENGTH) == day)).sum())
        l_done = int((lap_laps["day"] == day).sum())
        rows.append((f"Laps finished on day {day}", str(t_done), str(l_done), f"{t_done - l_done:+d}",
                     abs(t_done - l_done) <= LAPS_PER_DAY_TOLERANCE,
                     "Tick mode counts a lap on the day it finishes."))

        t_km = float(result["tick_distance_km"][tick_day == day].sum())
        l_km = l_done * lap_km
        diff_laps = (t_km - l_km) / lap_km
        rows.append((f"Distance on day {day}", f"{t_km:.1f} km", f"{l_km:.1f} km", f"{diff_laps:+.2f} laps",
                     abs(diff_laps) <= DISTANCE_PER_DAY_TOLERANCE_LAPS,
                     "Tick mode keeps driving an unfinished lap until driving stops; lap mode doesn't start it."))

    gap, times = result["gap_m"], result["tick_times"]
    drift = 0.0
    lap_laps_by_day = result["lap_laps"].groupby("day")["end"].max()
    for day, start, _ in result["windows"]:
        if day not in lap_laps_by_day:
            continue
        # Up to the end of lap mode's last lap that day, so tick mode's unfinished lap isn't counted
        in_day = (times >= start) & (times <= lap_laps_by_day[day])
        if in_day.any():
            day_gap = gap[in_day]
            drift = max(drift, float(np.max(np.abs(day_gap - day_gap[0]))))
    rows.append(("Biggest drift within a day", f"{drift:.0f} m", "", f"{drift / (lap_km * 1000):.2f} laps",
                 drift / (lap_km * 1000) <= DRIFT_TOLERANCE_LAPS,
                 "How far the cars drift apart during a day, up to lap mode's last lap. This is the timing check."))
    rows.append(("Biggest gap overall", f"{np.max(np.abs(gap)):.0f} m", "", "", None,
                 "Includes the unfinished laps tick mode carries over each night, which add up day by day."))
    return rows


# ----- Report -----

def provenance(args, models):
    def git(*cmd):
        try:
            return subprocess.run(["git", *cmd], cwd=REPO_ROOT, capture_output=True, text=True,
                                  check=True).stdout.strip()
        except Exception:
            return "unavailable"

    dirty = [line for line in git("status", "--porcelain").splitlines() if line.strip()]
    model = next(iter(models.values()))
    return [
        ("Run at", datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")),
        ("Command", "python -m scripts.compare_schedules " + shlex.join(sys.argv[1:])),
        ("Git commit", f"{git('rev-parse', '--short', 'HEAD')} on {git('rev-parse', '--abbrev-ref', 'HEAD')}"),
        ("Uncommitted changes", ", ".join(line[3:] for line in dirty) if dirty else "none"),
        ("Race / car", f"{args.race} / {args.car}"),
        ("Track", f"{len(model.gis.path_distances)} points, {model.gis.path_length:.1f} m per lap"),
        ("Within-lap pattern", str(OptimizedSpeedsPath.relative_to(REPO_ROOT))),
        ("Route cache", "Windows-style keys, read-only (--wsl-cache)" if args.wsl_cache else "normal"),
        ("Python", platform.python_version()),
    ]


def svg_chart(series, x_label, y_label, x_range, bands=(), height=240, zero_line=False):
    """A small line chart as inline SVG. `series` is [(label, xs, ys, css colour var)]."""
    width, left, right, top, bottom = 760, 64, 16, 14, 40
    plot_w, plot_h = width - left - right, height - top - bottom
    ys_all = np.concatenate([np.asarray(s[2], dtype=float) for s in series]) if series else np.array([0.0])
    y_min, y_max = float(np.nanmin(ys_all)), float(np.nanmax(ys_all))
    if zero_line:
        y_min, y_max = min(y_min, 0.0), max(y_max, 0.0)
    if y_max - y_min < 1e-9:
        y_min, y_max = y_min - 1, y_max + 1
    pad = (y_max - y_min) * 0.08
    y_min, y_max = y_min - pad, y_max + pad
    x_min, x_max = x_range

    def sx(x):
        return left + (np.asarray(x, dtype=float) - x_min) / (x_max - x_min) * plot_w

    def sy(y):
        return top + (1 - (np.asarray(y, dtype=float) - y_min) / (y_max - y_min)) * plot_h

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart">']
    for b0, b1 in bands:
        parts.append(f'<rect x="{sx(b0):.1f}" y="{top}" width="{sx(b1) - sx(b0):.1f}" height="{plot_h}" '
                     f'fill="var(--band)"/>')
    for tick in np.linspace(y_min + pad, y_max - pad, 5):
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{sy(tick):.1f}" y2="{sy(tick):.1f}" '
                     f'stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{left - 8}" y="{sy(tick) + 4:.1f}" text-anchor="end" class="tick">{tick:,.0f}</text>')
    if zero_line and y_min < 0 < y_max:
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" '
                     f'stroke="var(--fg-soft)" stroke-width="1"/>')
    for tick in np.linspace(x_min, x_max, 7):
        parts.append(f'<text x="{sx(tick):.1f}" y="{top + plot_h + 18}" text-anchor="middle" class="tick">{tick:,.0f}</text>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 4}" text-anchor="middle" class="axis">{html.escape(x_label)}</text>')
    parts.append(f'<text x="14" y="{top + plot_h / 2}" text-anchor="middle" class="axis" '
                 f'transform="rotate(-90 14 {top + plot_h / 2})">{html.escape(y_label)}</text>')
    for label, xs, ys, colour in series:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(sx(xs), sy(ys)))
        parts.append(f'<polyline points="{points}" fill="none" stroke="var({colour})" stroke-width="1.6" '
                     f'stroke-linejoin="round"><title>{html.escape(label)}</title></polyline>')
    parts.append("</svg>")
    return "".join(parts)


def scenario_html(result, rows):
    s = result["scenario"]
    marks = [r[4] for r in rows if r[4] is not None]
    verdict = "All within tolerance" if all(marks) else f"{marks.count(False)} outside tolerance"
    verdict_class = "ok" if all(marks) else "warn"

    table = ['<div class="table-wrap"><table><thead><tr><th>Measure</th><th class="tick-col">Tick mode</th>'
             '<th class="lap-col">Lap mode</th><th>Difference</th><th></th><th>Note</th></tr></thead><tbody>']
    for measure, t, l, d, ok, note in rows:
        mark = "" if ok is None else ('<span class="pill ok">✓ ok</span>' if ok else '<span class="pill warn">! check</span>')
        table.append(f"<tr><td>{measure}</td><td class=num>{t}</td><td class=num>{l}</td><td class=num>{d}</td>"
                     f"<td>{mark}</td><td class=note>{html.escape(note)}</td></tr>")
    table.append("</tbody></table></div>")

    hours = result["tick_times"] / 3600
    step = max(1, len(hours) // 1500)
    nights = []
    previous_end = 0.0
    for _, start, end in result["windows"]:
        nights.append((previous_end / 3600, start / 3600))
        previous_end = end
    nights.append((previous_end / 3600, hours[-1]))
    gap_chart = svg_chart([("Tick minus lap (m)", hours[::step], result["gap_m"][::step], "--tick")],
                          "Hours since midnight on day 0", "Tick mode ahead (m)", (0, hours[-1]),
                          bands=nights, zero_line=True)

    tl, ll = result["tick_laps"], result["lap_laps"]
    tl = tl[tl["complete"] & ~tl["crosses_night"]]
    n = max(len(ll), int(tl["lap"].max()) + 1 if len(tl) else 1)
    lap_chart = svg_chart([("Tick mode", tl["lap"], tl["moving_time"], "--tick"),
                           ("Lap mode", ll["lap"], ll["duration"], "--lap")],
                          "Lap number", "Lap time (s)", (0, n))

    return f"""
<section class="scenario">
  <header class="scenario-head">
    <h2>{html.escape(s.name)}</h2>
    <span class="pill {verdict_class}">{verdict}</span>
  </header>
  <p class="why">{html.escape(s.why)}</p>
  <p class="settings">Speeds per 10 laps: {", ".join(f"{v:g}" for v in s.block_speeds)} km/h (repeated) ·
    tick {s.tick} s · pattern {"on" if s.pattern else "off"} ·
    {len(result["lap_laps"])} laps in lap mode, {int(result["tick_laps"]["complete"].sum())} complete in tick mode</p>
  {"".join(table)}
  <div class="charts">
    <figure><figcaption>How far apart the two cars are through the race. Shaded: no driving allowed.</figcaption>{gap_chart}</figure>
    <figure><figcaption>Lap time, lap by lap. <span class="key tick">Tick mode</span> <span class="key lap">Lap mode</span></figcaption>{lap_chart}</figure>
  </div>
</section>"""


def write_report(path, results, summaries, prov, check):
    prov_rows = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in prov)
    check_html = (f'<p class="check">Tick-mode timing copy checked against a real <code>run_model</code>: '
                  f'{html.escape(check)}</p>' if check else "")
    sections = "".join(scenario_html(r, s) for r, s in zip(results, summaries))
    page = f"""<title>Lap vs Tick Schedules</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column; each scenario is a table then two charts. */
:root {{
  --bg: #f6f7f9; --panel: #ffffff; --fg: #1b2230; --fg-soft: #5a6577; --line: #dfe3ea;
  --grid: #e9ecf1; --band: #eef1f6; --tick: #2f5fbf; --lap: #c8741c;
  --ok: #1f7a4d; --ok-bg: #e3f3ea; --warn: #9a5b00; --warn-bg: #fbefd9;
  --sans: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #12161d; --panel: #1a2029; --fg: #e3e8f0; --fg-soft: #9aa6b8; --line: #2c3442;
  --grid: #232a35; --band: #1f2631; --tick: #7aa2ff; --lap: #f0a65a;
  --ok: #6fd3a0; --ok-bg: #173327; --warn: #f2bd6b; --warn-bg: #3a2c14; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #12161d; --panel: #1a2029; --fg: #e3e8f0; --fg-soft: #9aa6b8; --line: #2c3442;
  --grid: #232a35; --band: #1f2631; --tick: #7aa2ff; --lap: #f0a65a;
  --ok: #6fd3a0; --ok-bg: #173327; --warn: #f2bd6b; --warn-bg: #3a2c14; color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.55 var(--sans); }}
main {{ max-width: 960px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px; }}
h1 {{ font-size: 1.7rem; margin: 0; text-wrap: balance; }}
h2 {{ font-size: 1.15rem; margin: 0; text-wrap: balance; }}
.lede {{ color: var(--fg-soft); margin: 6px 0 0; max-width: 68ch; }}
code, .num, .prov td {{ font-family: var(--mono); font-size: .88em; }}
.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
thead th {{ font-size: .78rem; letter-spacing: .04em; text-transform: uppercase; color: var(--fg-soft); }}
.tick-col {{ color: var(--tick); }} .lap-col {{ color: var(--lap); }}
.note {{ color: var(--fg-soft); font-size: .88em; min-width: 220px; }}
.prov th {{ width: 180px; color: var(--fg-soft); font-weight: 600; }}
.prov td {{ word-break: break-word; }}
.pill {{ display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: .8rem; font-weight: 600; white-space: nowrap; }}
.pill.ok {{ background: var(--ok-bg); color: var(--ok); }} .pill.warn {{ background: var(--warn-bg); color: var(--warn); }}
.scenario {{ display: grid; gap: 12px; padding-top: 20px; border-top: 1px solid var(--line); }}
.scenario-head {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: baseline; justify-content: space-between; }}
.settings {{ margin: 0; color: var(--fg-soft); font-size: .9em; }}
.why {{ margin: 0; max-width: 72ch; }}
.charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
@media (max-width: 760px) {{ .charts {{ grid-template-columns: 1fr; }} }}
figure {{ margin: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px; min-width: 0; }}
figcaption {{ font-size: .85em; color: var(--fg-soft); margin-bottom: 4px; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart .tick {{ font: 11px var(--mono); fill: var(--fg-soft); }}
.chart .axis {{ font: 12px var(--sans); fill: var(--fg-soft); }}
.key::before {{ content: ""; display: inline-block; width: 14px; height: 3px; margin: 0 5px 3px 8px; vertical-align: middle; }}
.key.tick::before {{ background: var(--tick); }} .key.lap::before {{ background: var(--lap); }}
.check {{ margin: 0; font-size: .9em; }}
.howto pre {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; overflow-x: auto; font-family: var(--mono); font-size: .85em; }}
.howto ul {{ margin: 6px 0 0; padding-left: 20px; color: var(--fg-soft); }}
</style>
<main>
  <header>
    <h1>Lap vs Tick Schedules</h1>
    <p class="lede">Do tick mode and lap mode drive the same laps at the same times? Timing only: no
      weather, energy or battery. Both modes get the same model, speeds and within-lap pattern.</p>
  </header>
  <section>
    <h2>What was run</h2>
    <div class="table-wrap"><table class="prov"><tbody>{prov_rows}</tbody></table></div>
  </section>
  {check_html}
  {sections}
  <section class="howto">
    <h2>Rerun this</h2>
    <pre>.venv/bin/python -m scripts.compare_schedules --wsl-cache</pre>
    <ul>
      <li>One scenario: <code>--speeds 30,40 --tick 1</code> (km/h per 10 laps), <code>--no-pattern</code> to turn the pattern off.</li>
      <li><code>--check-against-run-model</code> also checks the tick-mode timing copy against a real run.</li>
      <li>Expected differences: tick mode keeps driving an unfinished lap until driving stops, then
        finishes it the next morning; lap mode doesn't start a lap that won't finish. With 10 s ticks and
        the pattern, tick mode reads the pattern at the wrong track point (the 3.6x bug in
        <code>logs/bugs.md</code>), so its lap times drift.</li>
    </ul>
  </section>
</main>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")


# ----- Setup and main -----

def use_windows_cache_keys(tiling):
    """
    Read-only workaround for WSL/Linux: the route cache was written on Windows, so its keys use '\\'.
    Also relabel the cached route's tiling to the config's (tiling doesn't change the route data).
    Never writes to the cache. Remove once the cache bug in `logs/bugs.md` is fixed.
    """
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


def build(args, tick):
    initial_conditions, environment, car = get_default_settings(args.race, args.car)
    hyperparameters = SimulationHyperparametersConfig.build_from({
        "simulation_period": tick,
        "return_type": SimulationReturnType.distance_and_time,
        "speed_dt": 1,
    })
    return build_model(environment, hyperparameters, initial_conditions, car)


def check_against_run_model(args, pattern_kmh):
    """Run real tick mode once (with a flat made-up forecast) and compare its distances with the copy."""
    from simulation.config import WeatherProvider

    model = build(args, 10)
    start = model.time_of_initialization - DAY_LENGTH  # a day either side, so local-time lookups stay inside
    times = np.arange(start, model.time_of_initialization + model.simulation_duration + DAY_LENGTH, 300)
    forecast = np.zeros((1, len(times), 6))
    forecast[0, :, 0] = times
    forecast[0, :, 1:3] = model.gis.launch_point
    forecast[0, :, 5] = 500.0  # sunlight, W/m²; only needed so the energy steps can run
    blocks = [30.0] * NUM_BLOCKS
    model.run_model(speed=np.array(blocks), weather=(forecast, WeatherProvider.Solcast), is_optimizer=True)
    real = np.asarray(model.get_results("distances"))
    _, _, copy_distance = tick_mode_timing(model, blocks, pattern_kmh)
    match = np.allclose(np.cumsum(copy_distance), real, rtol=0, atol=1e-9)
    return (f"{'identical' if match else 'DIFFERENT'} running distance at every tick "
            f"(30 km/h, pattern on, 10 s ticks, {len(real):,} ticks).")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--speeds", type=str, default=None,
                        help="Comma-separated km/h, one per 10 laps (repeated). Omit to run the default set.")
    parser.add_argument("--tick", type=int, default=1, help="Tick length in seconds for --speeds (default 1).")
    parser.add_argument("--no-pattern", action="store_true", help="Turn off the within-lap pattern for --speeds.")
    parser.add_argument("--race", default="FSGP")
    parser.add_argument("--car", default="Brightside")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"HTML report path (default {DEFAULT_OUT}).")
    parser.add_argument("--wsl-cache", action="store_true",
                        help="Read the Windows-written route cache on WSL/Linux (read-only).")
    parser.add_argument("--check-against-run-model", action="store_true",
                        help="Also check the tick-mode timing copy against a real run_model.")
    args = parser.parse_args()

    if args.wsl_cache:
        _, environment, _ = get_default_settings(args.race, args.car)
        use_windows_cache_keys(environment.competition_config.tiling)

    if args.speeds:
        speeds = [float(v) for v in args.speeds.split(",")]
        scenarios = [Scenario(f"{args.speeds} km/h, {'no pattern' if args.no_pattern else 'with pattern'}, "
                              f"{args.tick} s ticks", speeds, args.tick, not args.no_pattern)]
    else:
        scenarios = DEFAULT_SCENARIOS

    raw = np.load(OptimizedSpeedsPath)
    pattern_kmh = (raw - raw.mean()) / 2  # same normalisation tick mode applies (Simulation.py)

    models = {tick: build(args, tick) for tick in sorted({s.tick for s in scenarios})}
    lap_gis = LapGIS.from_gis(next(iter(models.values())).gis)

    results, summaries = [], []
    for scenario in scenarios:
        result = run_scenario(models[scenario.tick], lap_gis, scenario, pattern_kmh)
        rows = summarise(result)
        results.append(result)
        summaries.append(rows)

        print(f"\n{scenario.name}")
        if scenario.why:
            print(f"  ({scenario.why})")
        print(f"  {'Measure':<32}{'Tick mode':>14}{'Lap mode':>14}{'Difference':>14}")
        for measure, t, l, d, ok, _ in rows:
            mark = "" if ok is None else ("  ok" if ok else "  CHECK")
            print(f"  {measure:<32}{t:>14}{l:>14}{d:>14}{mark}")

    check = check_against_run_model(args, pattern_kmh) if args.check_against_run_model else ""
    if check:
        print(f"\nTick-mode timing copy vs real run_model: {check}")

    write_report(args.out, results, summaries, provenance(args, models), check)
    print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()

# Usage Guide

This guide describes how to use the various command line utilities that utilize `Simulation`, and presents a workflow for use during competition.

## Table of Contents
1. [FAQ and Introduction (_read this first!_)](#faq-and-introduction)
2. [Scripts](#scripts)
3. [Competition Workflow](#competition-workflow)

## FAQ and Introduction

All scripts in `simulation/cmd` should be run from the _root directory_, not from `simulation` or `simulation/cmd`. That is, the working directory (on UNIX-based systems, this is revealed with the `pwd` command), should be `Simulation`.

Additionally, you should have a virtual environment activated that satisfies the requirements listed in this repository.

If you get an error such as `ModuleNotFoundError: No module named 'simulation.model'` then `Simulation` is not properly in your `PYTHONPATH`, and you will need to add it.

Finally, all scripts will explain the options and flags available to them by running them with the  `-h` or `--help` flag. This document does _not_ repeat all the information that each script help blurb provides.
```bash
python3 simulation/cmd/run_simulation.py -h
```
Notice how the path provided is `simulation/cmd/run_simulation.py` as the working directory is `Simulation`.

## Scripts

These scripts are listed (approximately) by relevance.

### `optimize_simulation`

Execute the optimization sequence whereupon the optimal driving speeds for our solar car will be determined. The results will be saved in `config/speeds` (filename will be printed). This sequence will use the hyperparameters enumerated in `config/optimization_settings.json`. Importantly, the `--granularity` parameter controls the temporal granularity of the resulting optimized driving speeds. For example, `1` is hourly, `2` is bi-hourly, and `60` would be one driving speed per minute.

Accepts `--race_type`, `--granularity`.

### `run_simulation`

This is the primary entrypoint to `Simulation`. This will run simulation _once_, with either a default speed of 60km/h, or you can pass in the name of a saved speed array with the `--speeds` argument. Results will be printed, and graphs of various relevant time-series data will be plotted. If you provide `--speeds`, you'll also need to provide `--granularity` which should be the same as the value you passed into `optimize_simulation.py` when generating the speeds file you're providing.

Accepts `--race_type`, `--granularity`, `--verbose`, and `--speeds`.

### `update_environment`

Updates the stored weather forecasts and the current time in `config/initial_conditions_*.json` (`Simulation` needs to know the time that the weather forecasts were acquired in order to properly align them for calculations).

Accepts `--race`, and `--weather_provider`.

### `compile_races`

Compile ahead-of-time race data from `settings_*.json` race description files in `config`. This need only be ran once when cloning this repository, or if the race description files are updated.

Does not accept any arguments.

### `hyperparameter_search`

Execute the hyperparameter search sequence, which attempts various hyperparameter configurations described in `data/results/settings.json` and records the results in `data/results`.

Does not accept any arguments.

### `push_data`

Push local evolutions created by `hyperparameter_search` to our private database.

Does not accept any arguments.

### `cache_data`

Invoke calls to our weather or GIS APIs in order to gather external information, and cache the data for use in `Simulation`. Use the `--api` argument to specify what data is to be collected.
This should not be used to get weather forecasts unless you're certain know what you're doing and the consequences of not using `update_environment`.


## Competition Workflow

1. Run `compile_races`, and `cache_data` for GIS data once, if it hasn't been run before.
2. Run `update_environment` to gather weather forecasts and update time.
3. Update `initial_battery_charge` in `simulation/config/initial_conditions.json`.
4. Run `optimize_simulation`, and write down/copy the filename printed corresponding to the saved driving speeds.
5. Run `display_results`, passing in the filename of the saved driving speeds.
   1. Optionally, run `run_simulation`, passing in the filename of the saved driving speeds, to analyze the numerical simulation results in detail.
6. Repeat steps 2-5 as needed.

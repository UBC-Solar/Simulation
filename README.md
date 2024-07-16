# UBC Solar's ASC and FSGP Simulation

[![Build Status](https://app.travis-ci.com/UBC-Solar/Simulation.svg?branch=master)](https://app.travis-ci.com/UBC-Solar/Simulation)

Welcome to UBC Solar's race strategy simulation environment! The objective of this simulation is to guide UBC Solar's race strategy by creating a model to predict the performance of the UBC Solar cars in the American Solar Challenge (ASC) and Formula Sun Grand Prix (FSGP). 

This document contains information on how to get setup with the Simulation framework. 

For more detailed information on the inner workings of the simulation please refer to the [wiki](https://github.com/UBC-Solar/Simulation/wiki).

For instructions on how to use the scripts provided, see our [usage guide](simulation/cmd/USAGE_GUIDE.md).

## Getting started

### Prerequisites

- Python 3.9 or above (https://www.python.org/downloads/)
- Git version control (https://git-scm.com/downloads)
- pip Python package installer (should come with your Python installation)
- Rustc (Rust compiler) and Cargo (Rust package manager), versions >=1.77.2 recommended

Open up your terminal/command prompt and execute the following commands to check your installations.

- Ensure you have Git installed by running: 

```bash
git --version
```

- Check your Python installation by running:

```bash
python3 --version
```

Simulation uses compiled Rust to accelerate performance-critical functions. You'll need a Rust compiler. Check that your Rust compiler and package manager are accessible.

```bash
rustc --version
cargo --version
```

## Installation

- Clone the simulation repository into any directory of your choosing by running: 

    ```bash
    git clone https://github.com/UBC-Solar/Simulation.git
    ```

- You should now have a "Simulation" folder inside your chosen directory. To enter the "Simulation" folder run:

    ```bash
    cd Simulation
    ```

- Simulation uses `poetry` to manage dependencies. First, we will create a virtual environment. _Note: the second line is platform-dependent, and may be different for you._

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip3 install poetry
  ```

  - Now, use `poetry` to install dependencies.
  
  ```bash
  poetry install
  ```
  
  - Finally, compile the Rust libraries.
  ```bash
  maturin develop 
  ```

- You should then be able to run the command `simulation_health_check`, which will ensure everything is working properly.

  ```bash
  simulation_health_check
  ```
  You should see a dump of information ending with a "Simulation was successful!", indicating that everything worked properly.

## Preparing Simulation

- Simulation requires external data in order to construct the physical environment that our cars will traverse. As such, you'll need API keys for Google Maps's Directions API, and Solcast's Irradiance and Weather Forecast API. _UBC Solar members can acquire these from the Strategy Lead_.
  - Once you have acquired the necessary API keys, place them in a `.env` file, replacing `$your_key$` with your API keys.
    ```
    GOOGLE_MAPS_API_KEY=$your_key$
    SOLCAST_API_KEY=$your_key$
    ```
  - If you are trying to simulate FSGP, for example, modify `start_year`, `start_month`, and `start_day` in `simulation/config/settings_FSGP.json` as needed such that you are trying to simulate at a valid time for FSGP. Simulation can _only simulate the near future_, so if the dates are such that FSGP is in the past or distant future (beyond the length of the race) then it will fail to gather weather forecasts.
  - Now, run the following commands to invoke requests to the necessary APIs, which will cache the necessary data. See the [usage guide](simulation/cmd/USAGE_GUIDE.md) for further details on the scripts being invoked.
    ```bash
    python3 simulation/cmd/compile_races.py
    python3 simulation/cmd/cache_data.py --api WEATHER --race FSGP
    python3 simulation/cmd/update_environment.py --race FSGP
    ```

## Run Simulation

In order to learn how to use Simulation, please see our [usage guide](simulation/cmd/USAGE_GUIDE.md).


### Troubleshooting

You may run into Python path shenanigans, which is usually indicated by trying to run Simulation and getting `ModuleNotFoundError: no module named simulation.utils`. If this is the case, StackOverflow and Google will be your best friend but you can try the following command.
```bash
PYTHONPATH="/path/to/Simulation:$PYTHONPATH" && export PYTHONPATH
```

If you are having errors related to a specific package, it is likely that your system has installed an incompatible (usually too recent) version. It is known that the newest versions of Bokeh and Bayesian Optimization **WILL** cause errors to be raised.

# UBC Solar's ASC and FSGP Simulation

[![Build Status](https://app.travis-ci.com/UBC-Solar/Simulation.svg?branch=master)](https://app.travis-ci.com/UBC-Solar/Simulation)

Welcome to UBC Solar's race strategy simulation environment! The objective of this simulation is to guide UBC Solar's race strategy by creating a model to predict the performance of the UBC Solar cars in the American Solar Challenge (ASC) and Formula Sun Grand Prix (FSGP). 

This document contains information on how to get setup with the Simulation framework. 

For more detailed information on the inner workings of the simulation please refer to the [wiki](https://github.com/UBC-Solar/Simulation/wiki).

## Getting started

### Prerequisites

- Python 3.8 or above (https://www.python.org/downloads/)
- Git version control (https://git-scm.com/downloads)
- pip Python package installer (should come with your Python installation)

Open up your terminal/command prompt and execute the following commands to check your installations.

- Ensure you have Git installed by running: 

```bash
git --version
```

The above command should return a version number if you have Git installed.

- Check your Python installation by running:

```bash
python --version
```

NOTE: Any Python version before 3.8 is not supported so please make sure that your Python version is in the format 3.8.x or above.

## Installation

- Clone the simulation repository into any directory of your choosing by running: 

    ```bash
    git clone https://github.com/UBC-Solar/Simulation.git
    ```

- You should now have a "Simulation" folder inside your chosen directory. To enter the "Simulation" folder run:

    ```bash
    cd Simulation
    ```

- To install the simulation package, run the following:

    ```bash
    pip install .
    ```

    If the above command doesn't work, try the one below:

    ```bash
    pip3 install .
    ```

    If neither work, you either do not have pip installed or are not in the correct directory.

- Next, run the build command to complete the build which will attempt to compile a few libraries to improve performance.
    ```bash
    build_simulation
    ```
  You can also run the script directly by navigating to the "Simulation" project root directory. 
    ```bash
    python build.py
    ```

    If the above command doesn't work, try the one below:

    ```bash
    python3 build.py
    ```

- If all the commands worked, you should then be able to run the command `simulation_health_check`, which will ensure everything is working properly.

```bash
simulation_health_check
```
  You should see a dump of information ending with a "Simulation was successful!", indicating that everything worked properly.

## Run Simulation

To run Simulation, you can run the command `run_simulation`. This section covers command-line usage; to use Simulation as a part of a project, review the [wiki](https://github.com/UBC-Solar/Simulation/wiki).

```bash
run_simulation
```

#### Windows
Or, you can run the script directly. Before running the following commands make sure you have navigated to the "Simulation" directory. Please note support those in `examples` and `examples/archive` has discontinued.

#### Unix

```bash
python3 simulation/run_simulation.py
```
#### Windows

```bash
python .\simulation\run_simulation.py
```

### Arguments
In both cases, you can pass a set of execution parameters.
You can view a list of valid arguments and settings that Simulation can accept with the `-help` command.

#### Unix

```bash
python3 simulation/run_simulation.py -help
```
#### Windows

```bash
python .\simulation\run_simulation.py -help
```

### Testing

To run the pre-written tests and ensure the simulation package is functioning correctly, navigate to the "Simulation" folder on your terminal, and run:

``` bash
pytest
```

To run the tests and show the test coverage, do 
```
pip install pytest-cov
pytest --cov=simulation tests/
```

If your terminal returns something like "pytest is not recognized as an internal or external command...", install PyTest by executing the following:

``` bash
pip install -U pytest
```

Or:

```bash
pip3 install -U pytest
```

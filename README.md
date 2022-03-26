# UBC Solar's ASC and FSGP Simulation

[![Build Status](https://app.travis-ci.com/UBC-Solar/Simulation.svg?branch=master)](https://app.travis-ci.com/UBC-Solar/Simulation)

Welcome to UBC Solar's race strategy simulation environment! The objectve of this simulation is to guide UBC Solar's race strategy by creating a model to predict the performance of the UBC Solar cars in the American Solar Challenge (ASC) and Formula Sun Grand Prix (FSGP). 

This document contains information on how to getting started with using the simulation framework. 

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

### Installing the simulation package

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
    pip install -e .
    ```

    If the above command doesn't work, try the one below:

    ```bash
    pip3 install -e .
    ```

    If neither work, you either do not have pip installed or are not in the correct directory.

- If all the commands worked, you should then be able to import the simulation module in your Python (.py) scripts and use the simulation objects as shown below:

    ```python
    import simulation

    # creates a battery object
    battery = simulation.BasicBattery(0.90)
    ```

### Run an example simulation

To run an example simulation, you can either run the main Python script directly from your IDE or you can run it from your terminal. 
The following instructions are for running it from your terminal.

Before running the following commands make sure you have navigated to the "Simulation" folder on your terminal or the commands will not work. Please note support those in `examples/archive` has discontinued.

#### Ubuntu/MacOS

```bash
python3 examples/max_distance_from_speed_using_arrays.py
```
#### Windows

```bash
python .\examples\max_distance_from_speed_using_arrays.py
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

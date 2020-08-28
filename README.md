# Simulation

## Getting started

### Prerequisites

- Python 3 (Python 2.7 is not supported)
- pip Python package installer (should come with your Python installation)
- Git version control (https://git-scm.com/downloads)

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

Make sure that your Python version is in the format 3.x.x.

### Installing the simulation package

Clone the simulation repository into any directory using: 

```bash
git clone https://github.com/UBC-Solar/Simulation.git
```

To install the simulation package, navigate to the directory you cloned the repository into and run the following:

```bash
pip3 install -e .
```

You should then be able to import the simulation module into your Python (.py) scripts and use the simulation objects as shown below:

```python
import simulation

# creates a battery object
battery = simulation.BasicBattery(0.90)
```

## Run an example simulation:

#### Ubuntu/MacOS

```bash
python3 examples/max_distance_from_speed_using_arrays.py
```
#### Windows

```bash
python .\examples\max_distance_from_speed_using_arrays.py
```

## Testing

### Installation

``` bash
pip3 install -U pytest
```

### Run

To run the testing framework, navigate to the simulation directory and run the following:

``` bash
pytest
```

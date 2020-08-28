# Simulation

## Installation

#### Ubuntu
```bash
sudo apt update && sudo apt install python3-dev
pip3 install .
```

#### Mac OS X
```bash
TODO
```

#### Windows 10
Install the latest stable release from https://www.python.org/downloads/windows/

### Install using pip
First ensure you have Git installed by running: 

```bash
git --version
```

The command should return a version number if you have Git installed. If you do not have Git installed,
install the latest stable release from https://git-scm.com/downloads before moving on.

Clone the simulation repository into any directory using: 

```bash
git clone https://github.com/UBC-Solar/Simulation.git
```

To install the simulation package, navigate to the directory you cloned the repository into and run the following:

```bash
pip3 install -e .
```

You should then be able to import the simulation module into your Python (.py) scripts as shown below:

```python
import simulation
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
``` bash
pytest tests/
```

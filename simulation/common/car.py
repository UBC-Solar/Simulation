from simulation.config import config_directory
import os
import json

"""
This class stores constants for UBC Solar's solar-powered vehicles.
"""


class Car:
    """
    This class stores all physical constants describing a specific car.

    Data will be read from a "`car`.json" file located in `simulation/config/` for a given `car`.

    Data will be read in at runtime and made available through
    attribute access, such as `car.mass` or `car.tire_radius`.
    """
    def __init__(self, name: str):
        config_path = os.path.join(config_directory, f"{name}.json")

        with open(config_path) as f:
            car_constants = json.load(f)

        for attribute in car_constants:
            setattr(self, attribute, car_constants[attribute])

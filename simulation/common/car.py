from simulation.config import config_directory
import os
import json

"""
This class stores constants for UBC Solar's solar-powered vehicles.
"""


class Car:
    def __init__(self, name: str):
        config_path = os.path.join(config_directory, f"{name}.json")

        with open(config_path) as f:
            car_constants = json.load(f)

        for attribute in car_constants:
            setattr(self, attribute, car_constants[attribute])

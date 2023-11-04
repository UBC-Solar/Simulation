from simulation.config import config_directory
from simulation.utils import Singleton
import os
import json


class Race(metaclass=Singleton):
    def __init__(self, name: str):
        config_path = os.path.join(config_directory, f"{name}.json")

        with open(config_path) as f:
            race_constants = json.load(f)

        self.charging_begin = race_constants["charging_begin"]
        self.charging_end = race_constants["charging_end"]
        self.driving_begin = race_constants["driving_begin"]
        self.driving_end = race_constants["driving_end"]

from simulation.config import config_directory
import os
import json

"""
This class collects the constants that are related to a specific competition.
"""


class Race:
    def __init__(self, name: str):
        config_path = os.path.join(config_directory, f"settings_{name}.json")

        with open(config_path) as f:
            race_constants = json.load(f)

        self.charging_begin = race_constants["charging_begin"]
        self.charging_end = race_constants["charging_end"]
        self.driving_begin = race_constants["driving_begin"]
        self.driving_end = race_constants["driving_end"]
        self.tiling = race_constants["tiling"]
        self.date = (race_constants["start_year"], race_constants["start_month"], race_constants["start_day"])

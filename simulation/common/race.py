"""
This class collects the constants that are related to a specific competition.
"""
import pathlib

import numpy as np
import pickle
import enum
import json
import os


class Race:
    class RaceType(enum.Enum):
        ASC = "ASC"
        FSGP = "FSGP"

        def __str__(self):
            match self.value:
                case "ASC":
                    return "ASC"
                case "FSGP":
                    return "FSGP"

        def __reduce__(self):
            return self.__class__, (self.name,)

        def __contains__(self, item):
            return item == "ASC" or item == "FSGP"

        def __repr__(self):
            return str(self)

    ASC = RaceType.ASC
    FSGP = RaceType.FSGP

    def __init__(self, race_type: RaceType, race_constants: dict):
        self.race_type = race_type

        self.days = race_constants["days"]
        self.tiling = race_constants["tiling"]
        self.date = (race_constants["start_year"], race_constants["start_month"], race_constants["start_day"])

        self.race_duration = len(self.days) * 24 * 60 * 60  # Duration (s)
        self.driving_boolean = self.make_time_boolean("driving")
        self.charging_boolean = self.make_time_boolean("charging")

    def __str__(self):
        return str(self.race_type)

    def write(self, race_directory: pathlib.Path):
        with open(race_directory / f"{str(self.race_type)}.pkl", 'wb') as outfile:
            pickle.dump(self, outfile, protocol=pickle.HIGHEST_PROTOCOL)

    def make_time_boolean(self, boolean_type: str):
        boolean: np.ndarray = np.empty(self.race_duration, dtype=np.int8)
        DAY_LENGTH: int = 24 * 60 * 60  # Length of a day in seconds

        for tick in range(len(boolean)):
            day: int = tick // DAY_LENGTH    # Integer division to determine how many days have passed
            time_of_day = tick % DAY_LENGTH  # Time of day in seconds where 0 is midnight and 43200 is noon
            begin, end = self.days[str(day)][boolean_type]

            # If the time of day is between the beginning and end, then the boolean is True, else False
            boolean[tick] = begin <= time_of_day < end

        return boolean


def load_race(race_type: Race.RaceType, race_directory: pathlib.Path) -> Race:
    with open(race_directory / f"{str(race_type)}.pkl", 'rb') as infile:
        return pickle.load(infile)


def compile_races(config_directory: pathlib.Path, race_directory: pathlib.Path):
    fsgp_config_path = os.path.join(config_directory, f"settings_FSGP.json")
    asc_config_path = os.path.join(config_directory, f"settings_ASC.json")

    with open(fsgp_config_path) as f:
        fsgp_race_constants = json.load(f)

    with open(asc_config_path) as f:
        asc_race_constants = json.load(f)

    fsgp = Race(Race.FSGP, fsgp_race_constants)
    fsgp.write(race_directory)

    asc = Race(Race.ASC, asc_race_constants)
    asc.write(race_directory)

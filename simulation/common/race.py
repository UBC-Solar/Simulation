"""
This class collects the constants that are related to a specific competition.
"""
import enum

from simulation.config import config_directory
from simulation.cache.race import race_directory
import os
import json
import pickle
import numpy as np


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

    ASC = RaceType.ASC
    FSGP = RaceType.FSGP

    def __init__(self, race_type: RaceType):
        self.race_type = race_type

        config_path = os.path.join(config_directory, f"settings_{str(self.race_type)}.json")
        with open(config_path) as f:
            self.race_constants = json.load(f)
            race_constants = self.race_constants

        self.days = race_constants["days"]
        self.tiling = race_constants["tiling"]
        self.start_hour = race_constants["start_hour"]
        self.date = (race_constants["start_year"], race_constants["start_month"], race_constants["start_day"])

        self.race_duration = len(self.days) * 24 * 60 * 60  # Duration (s)
        self.driving_boolean = self.make_time_boolean("driving")
        self.charging_boolean = self.make_time_boolean("charging")

    def write(self):
        with open(race_directory / f"{str(self.race_type)}.pkl", 'wb') as outfile:
            pickle.dump(self, outfile, protocol=pickle.HIGHEST_PROTOCOL)

    def make_time_boolean(self, boolean_type: str):
        boolean: np.ndarray = np.empty(self.race_duration, dtype=np.int8)
        DAY_LENGTH: int = 24 * 60 * 60  # Length of a day in seconds
        start_time: int = self.start_hour * 3600

        for tick in range(len(boolean)):
            day: int = tick // DAY_LENGTH    # Integer division to determine how many days have passed
            time_of_day = tick % DAY_LENGTH  # Time of day in seconds where 0 is midnight and 43200 is noon
            begin, end = self.days[str(day)][boolean_type]

            # If the time of day is between the beginning and end, then the boolean is True, else False
            local_time = start_time + time_of_day
            boolean[tick] = begin <= local_time < end

        return boolean


def load_race(race_type):
    with open(race_directory / f"{str(race_type)}.pkl", 'rb') as infile:
        return pickle.load(infile)


if __name__ == "__main__":
    race = Race(Race.FSGP)
    race.write()

    race = Race(Race.ASC)
    race.write()


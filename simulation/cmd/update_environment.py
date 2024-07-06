import os
import argparse
import json
import datetime
import time
from dotenv import load_dotenv
from simulation.utils import Query
from simulation.utils.query import APIType
from simulation.config import config_directory
from simulation.common.race import Race, load_race


load_dotenv()


def main(race: str, weather_provider: str):
    # Grab the race start date from settings
    config_path = os.path.join(config_directory, f"settings_{race}.json")
    with open(config_path) as f:
        race_constants = json.load(f)

    race = load_race(Race.RaceType(race))

    date = datetime.datetime(race_constants["start_year"], race_constants["start_month"], race_constants["start_day"], 0, 0, 0)
    race_begin_timestamp = time.mktime(date.timetuple())
    current_timestamp = time.time()

    # Check if the current time makes sense (within race duration) and abort if not
    time_difference: float = current_timestamp - race_begin_timestamp  # Units: Seconds

    if time_difference < 0 or time_difference > race.race_duration:
        raise ValueError(f"Current time does not make sense for the current context. Is {date} the correct start date for {race}?")

    # Set the time (timezone-dependent UNIX time) in config
    initial_conditions_path = os.path.join(config_directory, f"initial_conditions_{race}.json")
    with open(initial_conditions_path, 'r') as file:
        initial_conditions = json.load(file)

    initial_conditions['start_time'] = int(time_difference)

    with open(initial_conditions_path, 'w') as file:
        json.dump(initial_conditions, file, indent=4)

    print(f"Time set to {datetime.datetime.now()}\n")

    # Finally, query the new environment data
    query: Query = Query(APIType.WEATHER, race, weather_provider)
    query.make()

    print("Environment updated successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", help="Race Acronym ['FSGP', 'ASC']")
    parser.add_argument("--weather_provider", help="Weather Provider ['SOLCAST', 'OPENWEATHER]", default='SOLCAST',
                        required=False)
    args = parser.parse_args()

    main(args.race, args.weather_provider)

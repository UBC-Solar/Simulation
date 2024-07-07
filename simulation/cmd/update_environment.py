import os
import argparse
import json
from datetime import datetime
import time
from dotenv import load_dotenv
from timezonefinder import TimezoneFinder
import pytz
from tzlocal import get_localzone
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

    # We need to get the timezone offset from the current position to the race position
    # for testing so that weather lines up properly
    point = race_constants["waypoints"][0]
    tf = TimezoneFinder()

    # Get the timezone name for the given latitude and longitude
    timezone_str = tf.timezone_at(lat=point[0], lng=point[1])
    if timezone_str is None:
        raise ValueError("Could not find timezone for the given coordinates.")

    # Get the timezone object for the target
    target_timezone = pytz.timezone(timezone_str)
    target_time = datetime.now(target_timezone)

    # Get the local timezone using tzlocal
    local_timezone = get_localzone()
    local_time = datetime.now(local_timezone)

    # Calculate the time difference in seconds
    timezone_difference = (target_time.utcoffset() - local_time.utcoffset()).total_seconds()

    # Get the current time, and the race start date in UNIX
    date = datetime(race_constants["start_year"], race_constants["start_month"], race_constants["start_day"], 0, 0, 0)
    race_begin_timestamp = time.mktime(date.timetuple())
    current_timestamp = time.time()

    # Check if the current time makes sense (within race duration) and abort if not
    elapsed_time: float = current_timestamp - race_begin_timestamp  # Units: Seconds

    if elapsed_time < 0 or elapsed_time > race.race_duration:
        raise ValueError(f"Current time does not make sense for the current context. Is {date} the correct start date for {race}?")

    # Set the time (timezone-dependent UNIX time) in config
    initial_conditions_path = os.path.join(config_directory, f"initial_conditions_{race}.json")
    with open(initial_conditions_path, 'r') as file:
        initial_conditions = json.load(file)

    initial_conditions['start_time'] = int(elapsed_time)
    initial_conditions['timezone_offset'] = timezone_difference

    with open(initial_conditions_path, 'w') as file:
        json.dump(initial_conditions, file, indent=4)

    print(f"Time set to {datetime.now()}\n")

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

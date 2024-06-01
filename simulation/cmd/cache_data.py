import math
import os
import sys
import json

import dill
import pytz
import requests
import argparse
import datetime
import polyline
import numpy as np
import pandas as pd
from tqdm import tqdm
from scipy import signal
from strenum import StrEnum
from dotenv import load_dotenv
from solcast import forecast
from timezonefinder import TimezoneFinder

from simulation.common.helpers import PJWHash
from simulation.config import config_directory
from simulation.cache.route import route_directory
from simulation.cache.weather import weather_directory
from simulation.common import constants, BrightSide, helpers, Race, load_race

# load API keys from environment variables
load_dotenv()


class APIType(StrEnum):
    GIS = "GIS"
    WEATHER = "WEATHER"
    ALL = "ALL"


class WeatherProvider(StrEnum):
    SOLCAST = "SOLCAST"
    OPENWEATHER = "OPENWEATHER"


# ------------------- GIS API -------------------
def cache_gis(race):
    """

    Makes calls to GIS API for coords of a given race and caches the results to a .npz file

    :param str race: either "FSGP" or "ASC"

    """
    print("Calling Google API and creating new route save file...\n")

    # Get path for race from setting JSONs 
    if race == "FSGP":
        race = load_race(Race.FSGP)
        route_file = route_directory / "route_data_FSGP.npz"

        # Coords will be the same as waypoints for FSGP
        origin_coord, dest_coord, coords, waypoints = get_fsgp_coords()

        tiling = race.tiling  # set tiling from config file
    else:
        race = load_race(Race.ASC)
        route_file = route_directory / "route_data.npz"

        # Get directions/path from directions API
        # Coords may not contain all waypoints for ASC
        origin_coord, dest_coord, coords, waypoints = get_asc_coords()

        tiling = race.tiling  # set tiling from config file

    # Calculate speed limits and curvature
    curvature = calculate_curvature(coords)
    coords = coords[:len(coords) - 1]  # Get rid of superfluous path coordinate at end
    speed_limits = calculate_speed_limits(coords, curvature)

    # Call Google Maps API
    path_elevations = calculate_path_elevations(coords)
    path_time_zones = calculate_time_zones(coords, race)

    # Tile results
    speed_limits = np.tile(speed_limits, tiling)
    path_elevations = np.tile(path_elevations, tiling)
    path_time_zones = np.tile(path_time_zones, tiling)
    coords = np.tile(coords, (tiling, 1))

    # Cache results
    with open(route_file, 'wb') as f:
        np.savez(f, path=coords, elevations=path_elevations, time_zones=path_time_zones,
                 origin_coord=origin_coord, dest_coord=dest_coord, speed_limits=speed_limits,
                 waypoints=waypoints, hash=get_hash(origin_coord, dest_coord, waypoints))


def get_fsgp_coords():
    """

    Returns the coords and waypoints of FSGP which are the same for FSGP

    :returns (coords, waypoints):
        coords = A NumPy array [n][latitude, longitude], marking out the path
        waypoints = A NumPy array [n][latitude, longitude] marking waypoints
    :rtype: tuple(np.ndarray, np.ndarray)

    """

    config_path = config_directory / f"settings_FSGP.json"
    with open(config_path) as f:
        model_parameters = json.load(f)

    origin_coord = model_parameters["origin_coord"]
    dest_coord = model_parameters["dest_coord"]
    waypoints = model_parameters["waypoints"]
    coords = waypoints  # Same for FSGP

    return origin_coord, dest_coord, coords, waypoints


def get_asc_coords():
    """

    Returns a path between the origin coordinate and the destination coordinate,
    passing through a group of optional waypoints.
    https://developers.google.com/maps/documentation/directions/start

    :returns (coords, waypoints):
        coords = A NumPy array [n][latitude, longitude], marking out the path
        waypoints = A NumPy array [n][latitude, longitude] marking waypoints
    :rtype: tuple(np.ndarray, np.ndarray)

    """

    config_path = config_directory / f"settings_ASC.json"

    with open(config_path) as f:
        model_parameters = json.load(f)

    origin_coord = model_parameters["origin_coord"]
    dest_coord = model_parameters["dest_coord"]
    waypoints = model_parameters["waypoints"]

    # set up URL
    url_head = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin_coord[0]},{origin_coord[1]}" \
               f"&destination={dest_coord[0]},{dest_coord[1]}"

    url_waypoints = ""
    if len(waypoints) != 0:

        url_waypoints = "&waypoints="

        if len(waypoints) > 10:
            print("Too many waypoints; Truncating to 10 waypoints total")
            waypoints = waypoints[0:10]

        for waypoint in waypoints:
            url_waypoints = url_waypoints + f"via:{waypoint[0]},{waypoint[1]}|"

        url_waypoints = url_waypoints[:-1]

    url_end = f"&key={os.environ['GOOGLE_MAPS_API_KEY']}"

    url = url_head + url_waypoints + url_end

    # HTTP GET
    r = requests.get(url)
    response = json.loads(r.text)

    path_points = []

    # If a route is found...
    if response['status'] == "OK":
        print("A route was found.\n")

        # Pick the first route in the list of available routes
        # A route consists of a series of legs
        for leg in response['routes'][0]['legs']:

            # Every leg contains an array of steps.
            for step in leg['steps']:
                # every step contains an encoded polyline
                polyline_raw = step['polyline']['points']
                polyline_coords = polyline.decode(polyline_raw)
                path_points = path_points + polyline_coords

        print("Route has been successfully retrieved!\n")

    else:
        print(f"No route was found: {response['status']}")
        print(f"Error Message: {response['error_message']}")

    route = np.array(path_points)

    # Removes duplicate coordinates to prevent gradient calculation errors
    if route.size != 0:
        duplicate_coordinate_indices = np.where((np.diff(route[:, 0]) == 0)) and np.where(
            (np.diff(route[:, 1]) == 0))
        route = np.delete(route, duplicate_coordinate_indices, axis=0)

    return origin_coord, dest_coord, route, waypoints


def calculate_path_elevations(coords):
    """

    Returns the elevations of every coordinate in the array of coordinates passed in as a coordinate
    See Error Message Interpretations: https://developers.google.com/maps/documentation/elevation/overview

    :param np.ndarray coords: A NumPy array [n][latitude, longitude]
    :returns: A NumPy array [n][elevation] in metres
    :rtype: np.ndarray

    """

    # construct URL
    url_head = 'https://maps.googleapis.com/maps/api/elevation/json?locations='

    location_strings = []
    locations = ""

    for coord in coords:

        locations = locations + f"{coord[0]},{coord[1]}|"

        if len(locations) > 8000:
            location_strings.append(locations[:-1])
            locations = ""

    if len(locations) != 0:
        location_strings.append(locations[:-1])

    url_tail = f"&key={os.environ['GOOGLE_MAPS_API_KEY']}"

    # Get elevations
    elevations = np.zeros(len(coords))

    i = 0
    with tqdm(total=len(location_strings), file=sys.stdout, desc="Acquiring Elevation Data") as pbar:
        for location_string in location_strings:
            url = url_head + location_string + url_tail

            r = requests.get(url)
            response = json.loads(r.text)
            pbar.update(1)

            if response['status'] == "OK":
                for result in response['results']:
                    elevations[i] = result['elevation']
                    i = i + 1

            elif response['status'] == "INVALID_REQUEST":
                sys.stderr.write("Error: Request was invalid\n")

            elif response['status'] == "OVER_DAILY_LIMIT":
                sys.stderr.write(
                    "Error: Possible causes - API key is missing or invalid, billing has not been enabled,"
                    " a self-imposed usage cap has been exceeded, or the provided payment method is no longer "
                    " valid. \n")

            elif response['status'] == "OVER_QUERY_LIMIT":
                sys.stderr.write("Error: Requester has exceeded quota\n")

            elif response['status'] == "REQUEST_DENIED":
                sys.stderr.write("Error: API could not complete the request\n")

    return elevations


def calculate_time_zones(coords, race: Race):
    """

    Takes in an array of coordinates, return the time zone relative to UTC, of each location in seconds

    :param np.ndarray coords: (float[N][lat lng]) array of coordinates
    :param str race: either "FSGP" or "ASC" as a string
    :returns np.ndarray time_diff: (float[N]) array of time differences in seconds

    """

    timezones_return = np.zeros(len(coords))

    tf = TimezoneFinder()
    dt = datetime.datetime(*race.date)

    with tqdm(total=len(coords), file=sys.stdout, desc="Calculating Time Zones") as pbar:
        for index, coord in enumerate(coords):
            pbar.update(1)
            tz_string = tf.timezone_at(lat=coord[0], lng=coord[1])
            timezone = pytz.timezone(tz_string)

            timezones_return[index] = timezone.utcoffset(dt).total_seconds()

    return timezones_return


# ------------------- Weather API -------------------
def cache_weather(race: Race, weather_provider: WeatherProvider):
    """

    Makes calls to Weather API for a given race and caches the results to a .npz file

    :param str race: either "FSGP" or "ASC"
    :param WeatherProvider weather_provider: enum representing which weather provider to use

    """
    print(f"Different weather data requested and/or weather file does not exist. "
          f"Calling {str(weather_provider)} API and creating weather save file...\n")

    # Get coords for race
    if race.race_type == Race.FSGP:
        # Get path/coords from cached file
        origin_coord, dest_coord, coords, waypoints = get_fsgp_coords()

        # For FSGP we can make the assumption that the weather will not change meaningfully
        # throughout the track, so just get weather for the first point
        coords = np.array([coords[0], coords[-1]])[0:1]

        weather_file = weather_directory / f"weather_data_FSGP_{str(weather_provider)}.npz"

    elif race.race_type == Race.ASC:
        # Get path/coords from cached file
        route_file = route_directory / "route_data.npz"

        if os.path.isfile(route_file):  # check there is a cached gis file
            with np.load(route_file) as gis_data:
                coords = gis_data['path']
                origin_coord = gis_data['origin_coord']
                dest_coord = gis_data['dest_coord']
                waypoints = gis_data['waypoints']
                coords = coords[::constants.REDUCTION_FACTOR]

        else:  # no cached file found -> get coords
            origin_coord, dest_coord, coords, waypoints = get_asc_coords()
            coords = coords[::constants.REDUCTION_FACTOR]

        weather_file = weather_directory / f"weather_data_{str(weather_provider)}.npz"

    else:
        raise NotImplementedError(f"Unsupported race type: {str(race)}!")

    with open(os.path.join(config_directory, f"settings_{str(race)}.json"), 'rt') as settings_file:
        race_configs = json.load(settings_file)

    with open(os.path.join(config_directory, f"initial_conditions_{str(race)}.json"), 'rt') as conditions_file:
        conditions = json.load(conditions_file)

    if weather_provider == WeatherProvider.OPENWEATHER:
        weather_forecast = update_path_weather_forecast_openweather(coords,
                                                                    race_configs["weather_freq"],
                                                                    int(race_configs["simulation_duration"] / 3600))
        with open(weather_file, 'wb') as f:
            np.savez(f, weather_forecast=weather_forecast, origin_coord=origin_coord,
                     dest_coord=dest_coord, hash=get_hash(origin_coord, dest_coord, waypoints),
                     provider=str(weather_provider))

    elif weather_provider == WeatherProvider.SOLCAST:
        racing_hours = len(race.days) * 24
        start_time = conditions["start_time"]
        raced_hours = start_time / 3600
        remaining_hours = math.floor(racing_hours - raced_hours)
        weather_forecast = update_path_weather_forecast_solcast(coords,
                                                                remaining_hours,
                                                                WeatherPeriod.Period(race_configs['period']),
                                                                race,
                                                                start_time)

        with open(weather_file, 'wb') as f:
            dill.dump({
                'weather_forecast': weather_forecast,
                'origin_coord': origin_coord,
                'dest_coord': dest_coord,
                'hash': get_hash(origin_coord, dest_coord, waypoints),
                'provider': str(weather_provider)
            }, f)
    else:
        raise NotImplementedError(f"Unsupported weather provider: {str(weather_provider)}!")


def update_path_weather_forecast_openweather(coords, weather_data_frequency, duration):
    """

    Passes in a list of coordinates, returns the hourly weather forecast
    for each of the coordinates

    :param np.ndarray coords: A NumPy array of [coord_index][2]
    - [2] => [latitude, longitude]
    :param str weather_data_frequency: Influences what resolution weather data is requested, must be one of
        "current", "hourly", or "daily"
    :param int duration: duration of weather requested, in hours

    :returns
    - A NumPy array [coord_index][N][9]
    - [coord_index]: the index of the coordinates passed into the function
    - [N]: is 1 for "current", 24 for "hourly", 8 for "daily"
    - [9]: (latitude, longitude, dt (UNIX time), timezone_offset (in seconds), dt + timezone_offset (local time),
           wind_speed, wind_direction, cloud_cover, description_id)

    """

    if int(duration) > 48 and weather_data_frequency == "hourly":
        time_length = {"current": 1, "hourly": 54, "daily": 8}
    else:
        time_length = {"current": 1, "hourly": 48, "daily": 8}

    num_coords = len(coords)

    weather_forecast = np.zeros((num_coords, time_length[weather_data_frequency], 9))

    with tqdm(total=len(coords), file=sys.stdout, desc="Calling OpenWeatherAPI") as pbar:
        for i, coord in enumerate(coords):
            weather_forecast[i] = get_coord_weather_forecast_openweather(coord, weather_data_frequency, int(duration))
            pbar.update(1)

    return weather_forecast


class WeatherPeriod:
    class Period(StrEnum):
        min_5 = '5min'
        min_10 = '10min'
        min_15 = '15min'
        min_20 = '20min'
        min_30 = '30min'
        min_60 = '60min'

    possible_periods: dict[Period, dict[str, float | str]] = {
        Period.min_5: {
            'formatted': 'PT5M',
            'hourly_rate': 20
        },
        Period.min_10: {
            'formatted': 'PT10M',
            'hourly_rate': 6
        },
        Period.min_15: {
            'formatted': 'PT15M',
            'hourly_rate': 4
        },
        Period.min_20: {
            'formatted': 'PT20M',
            'hourly_rate': 3
        },
        Period.min_30: {
            'formatted': 'PT30M',
            'hourly_rate': 2
        },
        Period.min_60: {
            'formatted': 'PT60M',
            'hourly_rate': 1
        }
    }


def update_path_weather_forecast_solcast(coords, duration, period: WeatherPeriod.Period, race, start_time):
    """

    Pass in a list of coordinates, returns the hourly weather forecast
    for each of the coordinates

    :param np.ndarray coords: A NumPy array of [coord_index][2]
    - [2] => [latitude, longitude]
    :param int duration: duration of weather requested, in hours
    :param WeatherPeriod.Period period: the period of time between forecast time points

    :returns
    - A NumPy array [coord_index][N][6]
    - [coord_index]: the index of the coordinates passed into the function
    - [N]: number of weather time points
    - [6]: period end UTC (UNIX time), latitude, longitude, wind_speed (m/s), wind_direction (degrees), ghi (W/m^2)

    """
    num_coords = len(coords)

    weather_forecast = np.zeros((num_coords, duration * WeatherPeriod.possible_periods[period]['hourly_rate'] + 1, 6))

    with tqdm(total=len(coords), file=sys.stdout, desc="Calling Solcast API") as pbar:
        for i, coord in enumerate(coords):
            weather_forecast[i] = get_coord_weather_forecast_solcast(coord, period, duration, race, start_time)
            pbar.update(1)

    return weather_forecast


def get_coord_weather_forecast_openweather(coord, weather_data_frequency, duration):
    """

    Passes in a single coordinate, returns a weather forecast
    for the coordinate depending on the entered "weather_data_frequency"
    argument. This function is unlikely to ever be called directly.

    :param np.ndarray coord: A single coordinate stored inside a NumPy array [latitude, longitude]
    :param str weather_data_frequency: Influences what resolution weather data is requested, must be one of
        "current", "hourly", or "daily"
    :param int  duration: amount of time simulated (in hours)

    :returns weather_array: [N][9]
    - [N]: is 1 for "current", 24 for "hourly", 8 for "daily"
    - [9]: (latitude, longitude, dt (UNIX time), timezone_offset (in seconds), dt + timezone_offset (local time),
           wind_speed, wind_direction, cloud_cover, description_id)
    :rtype: np.ndarray
    For reference to the API used:
    - https://openweathermap.org/api/one-call-api

    """

    # TODO: Who knows, maybe we want to run the simulation like a week into the future, when the weather forecast
    #   api only allows 24 hours of hourly forecast. I think it is good to pad the end of the weather_array with
    #   daily forecasts, after the hourly. Then in get_weather_forecast_in_time() the appropriate weather can be
    #   obtained by using the same shortest place method that you did with the cumulative distances.

    # ----- Building API URL -----

    # If current weather is chosen, only return the instantaneous weather
    # If hourly weather is chosen, then the first 24 hours of the data will use hourly data.
    # If the duration of the simulation is greater than 24 hours, then append on the daily weather forecast
    # up until the 7th day.

    data_frequencies = ["current", "hourly", "daily"]

    if weather_data_frequency in data_frequencies:
        data_frequencies.remove(weather_data_frequency)
    else:
        raise RuntimeError(
            f"\"weather_data_frequency\" argument is invalid. Must be one of {str(data_frequencies)}")

    exclude_string = ",".join(data_frequencies)

    url = f"https://api.openweathermap.org/data/2.5/onecall?lat={coord[0]}&lon={coord[1]}" \
          f"&exclude=minutely,{exclude_string}&appid={os.environ['OPENWEATHER_API_KEY']}"

    # ----- Calling OpenWeatherAPI ------

    r = requests.get(url)
    response = json.loads(r.text)

    # ----- Processing API response -----

    # Ensures that response[weather_data_frequency] is always a list of dictionaries
    if isinstance(response[weather_data_frequency], dict):
        weather_data_list = [response[weather_data_frequency]]
    else:
        weather_data_list = response[weather_data_frequency]

    # If the weather data is too long, then append the daily requests as well.
    if weather_data_frequency == "hourly" and duration > 24:

        url = f"https://api.openweathermap.org/data/2.5/onecall?lat={coord[0]}&lon={coord[1]}" \
              f"&exclude=minutely,hourly,current&appid={os.environ['OPENWEATHER_API_KEY']}"

        r = requests.get(url)
        response = json.loads(r.text)

        if isinstance(response["daily"], dict):
            weather_data_list = weather_data_list + [response["daily"]][2:]
        else:
            weather_data_list = weather_data_list + response["daily"][2:]

    """ weather_data_list is a list of weather forecast dictionaries.
        Weather dictionaries contain weather data points (wind speed, direction, cloud cover)
        for a given timestamp."""

    # ----- Packing weather data into a NumPy array -----

    weather_array = np.zeros((len(weather_data_list), 9))

    for i, weather_data_dict in enumerate(weather_data_list):
        weather_array[i][0] = coord[0]
        weather_array[i][1] = coord[1]
        weather_array[i][2] = weather_data_dict["dt"]
        weather_array[i][3] = response["timezone_offset"]
        weather_array[i][4] = weather_data_dict["dt"] + response["timezone_offset"]
        weather_array[i][5] = weather_data_dict["wind_speed"]

        # wind degrees follows the meteorological convention. So, 0 degrees means that the wind is blowing
        #   from the north to the south. Using the Azimuthal system, this would mean 180 degrees.
        #   90 degrees becomes 270 degrees, 180 degrees becomes 0 degrees, etc
        weather_array[i][6] = weather_data_dict["wind_deg"]
        weather_array[i][7] = weather_data_dict["clouds"]
        weather_array[i][8] = weather_data_dict["weather"][0]["id"]

    return weather_array


def get_coord_weather_forecast_solcast(coord, period: WeatherPeriod.Period, duration: int, race: Race, start_time):
    """

    Returns a weather forecast for the coordinate for ``duration`` with a granularity of ``period``.

    :param np.ndarray coord: A single coordinate stored inside a NumPy array [latitude, longitude]
    :param WeatherPeriod.Period period: granularity of the weather forecast
    :param int duration: amount of time simulated (in hours)

    :returns weather_array: [N][6]
    - [N]: number of weather timepoints
    - [6]: period end UTC (UNIX time), latitude, longitude, wind_speed (m/s), wind_direction (degrees), ghi (W/m^2)
    :rtype: np.ndarray

    For reference to the API used:
     - see https://docs.solcast.com.au/#49090b36-66db-4d0f-89d5-87d19f00bec1

    """

    wind_forecast = forecast.radiation_and_weather(
        latitude=coord[0],
        longitude=coord[1],
        hours=duration,
        period=WeatherPeriod.possible_periods[period]['formatted'],
        output_parameters=[
            'wind_speed_10m', 'wind_direction_10m'
        ],
    ).to_pandas()

    # We will have our arrays horizontal at all times while driving, but during the periods of time at the
    # beginning and end of the day we will tilt them to face the sun. So, make two API calls for
    # both options and apply a mask to pick from whichever one is valid given the rules for the day.
    tilted_ghi_forecast = forecast.radiation_and_weather(
        latitude=coord[0],
        longitude=coord[1],
        hours=duration,
        period=WeatherPeriod.possible_periods[period]['formatted'],
        output_parameters=[
            'gti'
        ],
    ).to_pandas()

    untilted_ghi_forecast = forecast.radiation_and_weather(
        latitude=coord[0],
        longitude=coord[1],
        hours=duration,
        tilt=0,
        period=WeatherPeriod.possible_periods[period]['formatted'],
        output_parameters=[
            'gti',
        ],
    ).to_pandas()

    temporal_period = int(60 * 60 / WeatherPeriod.possible_periods[period]['hourly_rate'])
    irradiance_forecast: pd.DataFrame = apply_stationary_charging_mask(tilted_ghi_forecast, untilted_ghi_forecast, race,
                                                                        temporal_period, start_time)

    weather_forecast: pd.DataFrame = wind_forecast.join(irradiance_forecast)

    weather_array = np.zeros((len(weather_forecast), 6))
    for i, (time, weather) in enumerate(wind_forecast.join(irradiance_forecast).iterrows()):
        time_dt: int = int(time.timestamp())  # ``time`` will be a pandas.time.Timestamp object
        latitude: float = coord[0]
        longitude: float = coord[1]
        wind_speed: float = weather['wind_speed_10m']
        wind_direction: float = weather['wind_direction_10m']
        ghi: float = weather['dni'] + weather['dhi']

        weather_array[i] = np.array([time_dt, latitude, longitude, wind_speed, wind_direction, ghi])

    return weather_array


def apply_stationary_charging_mask(tilted_ghi_forecast, untilted_ghi_forecast, race: Race, period: int,
                                   start_time: int):
    driving_mask = race.driving_boolean
    charging_mask = race.charging_boolean
    stationary_mask = np.logical_and(charging_mask, np.logical_not(driving_mask))
    stationary_mask = stationary_mask[start_time:]

    tilted_ghi = tilted_ghi_forecast["gti"]
    untilted_ghi = untilted_ghi_forecast["gti"]

    mask = stationary_mask[::period]
    # It is fair to pad with False and assume we won't be charging at the end
    # because the last element will always correspond to the end of the race
    mask = match_sizes(mask, untilted_ghi, False)

    untilted_ghi_forecast["gti"] = np.where(mask, tilted_ghi, untilted_ghi)

    return tilted_ghi_forecast


# ------------------- Helpers ------------------
def match_sizes(array_1: np.ndarray, array_2: np.ndarray, pad_element) -> np.ndarray:
    """
    Match the length of ``array_1`` to ``array_2`` by removing elements of ``array_1`` from
    the back first, or pad with elements of kind ``pad_element``.

    Does nothing if the lengths already match.

    :param np.ndarray array_1: Array that will be modified
    :param np.ndarray array_2: Reference array
    :param pad_element: Value that will be used for padding
    :return: Modified array
    """

    if len(array_1) > len(array_2):
        while len(array_1) > len(array_2):
            array_1 = array_1[:-1]
    elif len(array_1) < len(array_2):
        while len(array_1) < len(array_2):
            array_1 = np.append(array_1, pad_element)

    return array_1


def linearly_interpolate(x, y, t):
    return (y - x) * t + x


def calculate_speed_limits(path, curvature) -> np.ndarray:
    cumulative_path_distances = np.cumsum(helpers.calculate_path_distances(path))
    speed_limits = np.empty([int(cumulative_path_distances[-1]) + 1], dtype=int)

    for i in range(int(cumulative_path_distances[-1]) + 1):
        gis_index = closest_index(i, cumulative_path_distances)
        speed_limit = linearly_interpolate(BrightSide.max_cruising_speed,
                                           BrightSide.max_speed_during_turn,
                                           curvature[gis_index])
        speed_limits[i] = speed_limit

    return speed_limits


def calculate_curvature(path):
    displacement: np.ndarray = np.diff(path, axis=0)
    cos_theta: np.ndarray = np.empty(displacement.shape[0])

    def calculate_cos_theta(u, v) -> float:
        return np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))

    offset_displacement = np.roll(displacement, (1, 1))

    for i in range(0, len(cos_theta)):
        cos_theta[i] = calculate_cos_theta(displacement[i], offset_displacement[i])

    angles: np.ndarray = np.abs(np.arccos(cos_theta))
    filtered: np.ndarray = signal.savgol_filter(angles, 5, 2)
    normalized: np.ndarray = (filtered - filtered.min()) / (filtered - filtered.min()).max()

    return normalized


def closest_index(target_distance, distances):
    return np.argmin(np.abs(distances - target_distance))


def get_hash(origin_coord, dest_coord, waypoints):
    """

    Makes a hashed key from the inputted waypoints

    :param np.ndarray origin_coord: A NumPy array of the waypoints [latitude, longitude] of a race
    :param np.ndarray dest_coord: A NumPy array of the waypoints [latitude, longitude] of a race
    :param np.ndarray waypoints: A NumPy array of the waypoints [latitude, longitude] of a race
    :return: Returns the generated hash
    :rtype: int

    """

    hash_string = str(origin_coord) + str(dest_coord)
    for value in waypoints:
        hash_string += str(value)
    filtered_hash_string = "".join(filter(str.isnumeric, hash_string))
    return PJWHash(filtered_hash_string)


class Query:
    def __init__(self, api_type, race_type, weather_provider):
        self.api: APIType = APIType(api_type)
        self.race: Race = load_race(race_type)
        self.provider: WeatherProvider = WeatherProvider(weather_provider)

    def make(self):
        # Fetch APIs
        if self.api == APIType.GIS or self.api == APIType.ALL:
            cache_gis(str(self.race))

        if self.api == APIType.WEATHER or self.api == APIType.ALL:
            cache_weather(self.race, self.provider)


# ------------------- Script -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", help="Race Acronym ['FSGP', 'ASC']")
    parser.add_argument("--api", help="API(s) to cache ['GIS', 'WEATHER', 'ALL']")
    parser.add_argument("--weather_provider", help="Weather Provider ['SOLCAST', 'OPENWEATHER]", default='SOLCAST',
                        required=False)
    args = parser.parse_args()

    query: Query = Query(args.api, args.race, args.weather_provider)
    query.make()

import os
import sys
import json
import pytz
import requests
import argparse
import datetime
import polyline
import numpy as np
from tqdm import tqdm
from xml.dom import minidom
from dotenv import load_dotenv
from timezonefinder import TimezoneFinder
from simulation.common.helpers import PJWHash
from simulation.common import ASC, FSGP, constants
from simulation.config import config_directory
from simulation.cache.route import route_directory
from simulation.cache.weather import weather_directory

import matplotlib.pyplot as plt

# Const vars
SIM_DUR = 432000                    # duration of the simulation in seconds (432000s = 5 days)
WEATHER_DURATION = SIM_DUR/3600     # duration of weather to be fetched
WEATHER_FREQ = "daily"              # can be "current", "hourly", or "daily"


# load API keys from environment variables
load_dotenv()
print("loaded environment vars")


# ------------------- GIS API -------------------
def cache_gis(race):
    """

    Makes calls to GIS API for coords of a given race and caches the results to a .npz file

    :param str race: either "FSGP" or "ASC"

    """
    print("Calling Google API and creating new route save file...\n")

    # Get path for race
    if race == "FSGP":
        # Get path/coords from KMZ file for FSGP
        # Coords will be the same as waypoints for FSGP
        origin_coord, dest_coord, coords, waypoints = get_fsgp_coords()
        route_file = route_directory / "route_data_FSGP.npz"
    else:
        # Get directions/path from directions API
        # Coords may not contain all waypoints for ASC
        origin_coord, dest_coord, coords, waypoints = get_asc_coords()
        route_file = route_directory / "route_data.npz"

    # Call Google Maps API
    path_elevations = calculate_path_elevations(coords)
    path_time_zones = calculate_time_zones(coords, race)

    print(path_elevations)
    print(path_time_zones)

    with open(route_file, 'wb') as f:
        np.savez(f, path=coords, elevations=path_elevations, time_zones=path_time_zones,
                 origin_coord=origin_coord, dest_coord=dest_coord,
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
    coords, waypoints = model_parameters["waypoints"]

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

    print(response)

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


def calculate_time_zones(coords, race):
    """

    Takes in an array of coordinates, return the time zone relative to UTC, of each location in seconds

    :param np.ndarray coords: (float[N][lat lng]) array of coordinates
    :param str race: either "FSGP" or "ASC" as a string
    :returns np.ndarray time_diff: (float[N]) array of time differences in seconds

    """

    timezones_return = np.zeros(len(coords))

    tf = TimezoneFinder()

    if race == "FSGP":
        # this is when FSGP 2021 starts
        dt = datetime.datetime(*FSGP.date)
    else:
        # this is when ASC 2021 starts
        dt = datetime.datetime(*ASC.date)

    with tqdm(total=len(coords), file=sys.stdout, desc="Calculating Time Zones") as pbar:
        for index, coord in enumerate(coords):
            pbar.update(1)
            tz_string = tf.timezone_at(lat=coord[0], lng=coord[1])
            timezone = pytz.timezone(tz_string)

            timezones_return[index] = timezone.utcoffset(dt).total_seconds()

    return timezones_return


# ------------------- Weather API -------------------
def cache_weather(race):
    """

    Makes calls to Weather API for a given race and caches the results to a .npz file

    :param str race: either "FSGP" or "ASC"

    """
    print("Different weather data requested and/or weather file does not exist. "
          "Calling OpenWeather API and creating weather save file...\n")

    # Get coords for race
    if race == "FSGP":
        # Get path/coords from cached file
        origin_coord, dest_coord, coords, waypoints = get_fsgp_coords()
        coords = np.array([coords[0], coords[-1]])

        weather_file = weather_directory / "weather_data_FSGP.npz"
    else:
        # Get path/coords from cached file
        route_file = route_directory / "route_data.npz"

        if os.path.isfile(route_file):  # check there is a cached gis file
            with np.load(route_file) as gis_data:
                coords = gis_data['path']
                origin_coord = gis_data['origin_coord']
                dest_coord = gis_data['dest_coord']
                coords = coords[::constants.REDUCTION_FACTOR]

        else:  # no cached file found -> get coords
            origin_coord, dest_coord, coords, waypoints = get_asc_coords()
            coords = coords[::constants.REDUCTION_FACTOR]

        weather_file = weather_directory / "weather_data.npz"

    weather_forecast = update_path_weather_forecast(coords, WEATHER_FREQ, int(WEATHER_DURATION))

    with open(weather_file, 'wb') as f:
        np.savez(f, weather_forecast=weather_forecast, origin_coord=origin_coord,
                 dest_coord=dest_coord, hash=get_hash(origin_coord, dest_coord, waypoints))


def update_path_weather_forecast(coords, weather_data_frequency, duration):
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
            weather_forecast[i] = get_coord_weather_forecast(coord, weather_data_frequency, int(duration))
            pbar.update(1)

    return weather_forecast


def get_coord_weather_forecast(coord, weather_data_frequency, duration):
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

        # wind degrees follows the meteorlogical convention. So, 0 degrees means that the wind is blowing
        #   from the north to the south. Using the Azimuthal system, this would mean 180 degrees.
        #   90 degrees becomes 270 degrees, 180 degrees becomes 0 degrees, etc
        weather_array[i][6] = weather_data_dict["wind_deg"]
        weather_array[i][7] = weather_data_dict["clouds"]
        weather_array[i][8] = weather_data_dict["weather"][0]["id"]

    return weather_array


# ------------------- Helpers ------------------
def get_hash(origin_coord, dest_coord, waypoints):
    """

    Makes a hashed key from the inputted waypoints

    :param np.ndarray waypoints: A NumPy array of the waypoints [latitude, longitude] of a race
    :return: Returns the generated hash
    :rtype: int

    """

    hash_string = str(origin_coord) + str(dest_coord)
    for value in waypoints:
        hash_string += str(value)
    filtered_hash_string = "".join(filter(str.isnumeric, hash_string))
    return PJWHash(filtered_hash_string)


def parse_coordinates_from_kml(coords_str: str) -> np.ndarray:
    """

    Parse a coordinates string from a XML (KML) file into a list of coordinates (2D vectors).
    Requires coordinates in the format "39., 41., 0  39., 40., 0" which will return [ [39., 41.], [39., 40.] ].

    :param coords_str: coordinates string from a XML (KML) file
    :return: list of 2D vectors representing coordinates
    :rtype: np.ndarray

    """

    def parse_coord(pair):
        coord = pair.split(',')
        coord.pop()
        coord = [float(value) for value in coord]
        return coord

    coords = list(map(parse_coord, coords_str.split()))
    return np.array(coords)


# ------------------- Script -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("race", help="Race Acronym ['FSGP', 'ASC']")
    parser.add_argument("api", help="API(s) to cache ['GIS', 'WEATHER', 'ALL']")
    args = parser.parse_args()

    # TODO: debug prints remove later
    print(f"Race Acronym: {args.race}")
    print(f"API: {args.api}")

    print(os.environ['GOOGLE_MAPS_API_KEY'])

    # Parse Args fields, handle invalid inputs
    fetch_gis = False
    fetch_weather = False

    if args.api == "ALL":
        fetch_gis = True
        fetch_weather = True
    elif args.api == "GIS":
        fetch_gis = True
    elif args.api == "WEATHER":
        fetch_weather = True
    else:
        print("API field input is invalid")
        exit()

    if args.race != "FSGP" and args.race != "ASC":
        print("Race field input is invalid")
        exit()

    # Fetch APIs
    if fetch_gis:
        cache_gis(args.race)

    if fetch_weather:
        cache_weather(args.race)

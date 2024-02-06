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
from dotenv import load_dotenv
from timezonefinder import TimezoneFinder
from simulation.cache.route import route_directory
from simulation.common import ASC, FSGP

# load API keys from environment variables
load_dotenv()
print("loaded environment vars")


# ------------------- GIS API -------------------
def cache_gis(race):
    print("Calling Google API and creating new route save file...\n")

    # Get path for race
    if race == "FSGP":
        # Get path/coords from KMZ file for FSGP
        # Coords will be the same as waypoints for FSGP
        coords, waypoints = get_fsgp_coords()
        route_file = route_directory / "route_data_FSGP.npz"
    else:
        # Get directions/path from directions API
        # Coords may not contain all waypoints for ASC
        coords, waypoints = get_asc_coords()
        route_file = route_directory / "route_data.npz"

    # Call Google Maps API
    path_elevations = calculate_path_elevations(coords)
    path_time_zones = calculate_time_zones(coords, race)

    # TODO: Figure out what to do with hash_key
    with open(route_file, 'wb') as f:
        np.savez(f, path=coords, elevations=path_elevations, time_zones=path_time_zones,
                 origin_coord=coords[0], dest_coord=coords[-1],
                 waypoints=waypoints, hash=1234)


def get_fsgp_coords():
    coords = []
    waypoints = []

    return coords, waypoints

def get_asc_coords():
    """

    Returns a path between the origin coordinate and the destination coordinate,
    passing through a group of optional waypoints.
    https://developers.google.com/maps/documentation/directions/start

    :param np.ndarray origin_coord: A NumPy array [latitude, longitude] of the starting coordinate
    :param np.ndarray dest_coord: A NumPy array [latitude, longitude] of the destination coordinate
    :param list waypoints: A NumPy array [n][latitude, longitude], where n<=10
    :returns: A NumPy array [n][latitude, longitude], marking out the path.
    :rtype: np.ndarray

    """

    # TODO: Setup these initial params
    origin_coord = []
    dest_coord = []
    waypoints = []

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

    return route, waypoints


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
def cache_weather():
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("race", help="Race Acronym ['FSGP', 'ASC']")
    parser.add_argument("api", help="API(s) to cache ['GIS', 'WEATHER', 'ALL']")
    args = parser.parse_args()

    print(f"Race Acronym: {args.race}")
    print(f"API: {type(args.race)}")

    print(os.environ['GOOGLE_MAPS_API_KEY'])

    # Parse Args fields
    fetch_gis = False
    fetch_weather = False

    if args.api == "BOTH":
        fetch_gis = True
        fetch_weather = True
    elif args.api == "GIS":
        fetch_gis = True
    elif args.api == "WEATHER":
        fetch_weather = True
    else:
        print("API field input is invalid")
        exit()

    if args.race != "FSGP" or args.race != "ASC":
        print("Race field input is invalid")
        exit()

    if fetch_gis:
        cache_gis(args.race)

    if fetch_weather:
        cache_weather()







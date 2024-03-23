import datetime
import os
import json
import logging
import math
import numpy as np
import sys

from simulation.cache.route import route_directory
from simulation.common import helpers, ASC, FSGP, BrightSide
from simulation.config import config_directory
from dotenv import load_dotenv
from tqdm import tqdm
from sklearn.neighbors import BallTree
from math import radians
from xml.dom import minidom
import core


class GIS:
    def __init__(self, api_key, origin_coord, dest_coord, waypoints, race_type, current_coord=None, hash_key=None):
        """

        Initialises a GIS (geographic location system) object. This object is responsible for getting the
        simulation's planned route from the Google Maps API and performing operations on the received data.

        :param api_key: API key that allows access to the Google Maps API
        :param origin_coord: NumPy array containing the start coordinate (lat, long) of the planned travel route
        :param dest_coord: NumPy array containing the end coordinate (lat, long) of the planned travel route
        :param waypoints: NumPy array containing the route waypoints to travel through during simulation
        :param race_type: String ("FSGP" or "ASC") stating which race is being simulated
        :param hash_key: key used to identify cached data as valid for a Simulation model

        """

        self.api_key = api_key

        self.current_index = 0
        self.distance_remainder = 0

        self.origin_coord = origin_coord
        self.dest_coord = dest_coord
        self.current_coord = current_coord
        self.waypoints = waypoints
        self.race_type = race_type

        # path to file storing the route and elevation NumPy arrays
        if self.race_type == "FSGP":
            route_file = route_directory / "route_data_FSGP.npz"
        else:
            route_file = route_directory / "route_data.npz"

        # if the file exists, load path from file
        if os.path.isfile(route_file):
            with np.load(route_file) as route_data:
                if route_data['hash'] == hash_key:

                    print("Previous route save file is being used...\n")

                    print("----- Route save file information -----")
                    for key in route_data:
                        print(f"> {key}: {route_data[key].shape}")

                    self.path = route_data['path']
                    self.launch_point = route_data['path'][0]
                    self.path_elevations = route_data['elevations']
                    self.path_time_zones = route_data['time_zones']
                    self.speed_limits = route_data['speed_limits']

                    if current_coord is not None:
                        if not np.array_equal(current_coord, origin_coord):
                            logging.warning("Current position is not origin position. Modifying path data.\n")

                            # We need to find the closest coordinate along the path to the vehicle position
                            current_coord_index = GIS.find_closest_coordinate_index(current_coord, self.path)

                            # All coords before the current coordinate should be discarded
                            self.path = self.path[current_coord_index:]
                            self.path_elevations = self.path_elevations[current_coord_index:]
                            self.path_time_zones = self.path_time_zones[current_coord_index:]
        else:
            logging.warning("Route save file does not exist.\n")
            logging.error("Update API cache by calling CacheAPI.py , Exiting simulation...\n")

            exit()

        self.path_distances = helpers.calculate_path_distances(self.path)
        self.path_gradients = helpers.calculate_path_gradients(self.path_elevations, self.path_distances)

    @staticmethod
    def process_KML_file(route_file):
        """

        Load the FSGP Track from a KML file exported from a Google Earth project.

        Ensure to follow guidelines enumerated in this directory's `README.md` when creating and
        loading new route files.

        :return: Array of N coordinates (latitude, longitude) in the shape [N][2].
        """
        with open(route_file) as f:
            data = minidom.parse(f)
            kml_coordinates = data.getElementsByTagName("coordinates")[0].childNodes[0].data
            coordinates: np.ndarray = np.array(helpers.parse_coordinates_from_kml(kml_coordinates))

            # Google Earth exports coordinates in order longitude, latitude, when we want the opposite
            return np.roll(coordinates, 1, axis=1)

    def calculate_closest_gis_indices(self, cumulative_distances):
        """

        Takes in an array of point distances from starting point, returns a list of
        self.path indices of coordinates which have a distance from the starting point
        closest to the point distances.

        :param np.ndarray cumulative_distances: (float[N]) array of distances, where cumulative_distances[x] > cumulative_distances[x-1]
        :returns: (float[N]) array of indices of path
        :rtype: np.ndarray

        """

        path_distances = self.path_distances.copy()
        cumulative_path_distances = np.cumsum(path_distances)
        cumulative_path_distances[::2] *= -1
        average_distances = np.abs(np.diff(cumulative_path_distances) / 2)


        return core.closest_gis_indices_loop(cumulative_distances, average_distances)

    def python_calculate_closest_gis_indices(self, cumulative_distances, average_distances):
        """

        Python implementation of rust core.closest_gis_indices_loop. See parent function for documentation details.

        """

        current_coordinate_index = 0
        result = []

        with tqdm(total=len(cumulative_distances), file=sys.stdout, desc="Calculating closest GIS indices") as pbar:
            for distance in np.nditer(cumulative_distances):
                if distance > average_distances[current_coordinate_index]:
                    if current_coordinate_index > len(average_distances) - 1:
                        current_coordinate_index = len(average_distances) - 1
                    else:
                        current_coordinate_index += 1
                        if current_coordinate_index > len(average_distances) - 1:
                            current_coordinate_index = len(average_distances) - 1

                result.append(current_coordinate_index)

                pbar.update(1)

        return np.array(result)

    # ----- Getters -----
    def get_time_zones(self, gis_indices):
        """

        Takes in an array of path indices, returns the time zone at each index

        :param np.ndarray gis_indices: (float[N]) array of path indices
        :returns: (float[N]) array of time zones in seconds
        :rtype: np.ndarray

        """

        return self.path_time_zones[gis_indices]

    def get_gradients(self, gis_indices):
        """

        Takes in an array of path indices, returns the road gradient at each index

        :param np.ndarray gis_indices: (float[N]) array of path indices
        :returns: (float[N]) array of road gradients
        :rtype np.ndarray:

        """

        return self.path_gradients[gis_indices]

    def get_path(self):
        """
        Returns all N coordinates of the path in a NumPy array
        [N][latitude, longitude]

        :rtype: np.ndarray

        """

        return self.path

    def get_path_elevations(self):
        """

        Returns all N elevations of the path in a NumPy array
        [N][elevation]

        :rtype: np.ndarray

        """

        return self.path_elevations

    def get_path_distances(self):
        """

        Returns all N-1 distances of the path in a NumPy array
        [N-1][elevation]

        :rtype: np.ndarray

        """

        return self.path_distances

    def get_path_gradients(self):
        """

        Returns all N-1 gradients of a path in a NumPy array
        [N-1][gradient]

        :rtype: np.ndarray

        """

        return self.path_gradients

    # ----- Path calculation functions -----
    def calculate_path_min_max(self):  # DEPRECATED
        logging.warning(f"Using deprecated function 'calculate_path_min_max()'!")
        min_lat, min_long = self.path.min(axis=0)
        max_lat, max_long = self.path.max(axis=0)
        return [min_long, min_lat, max_long, max_lat]

    def calculate_current_heading_array(self):
        """

        Calculates the bearing of the vehicle between consecutive points
        https://www.movable-type.co.uk/scripts/latlong.html

        :returns: array of bearings
        :rtype: np.ndarray

        """
        bearing_array = np.zeros(len(self.path))

        for index in range(0, len(self.path) - 1):
            coord_1 = np.radians(self.path[index])
            coord_2 = np.radians(self.path[index + 1])

            y = math.sin(coord_2[1] - coord_1[1]) \
                * math.cos(coord_2[0])

            x = math.cos(coord_1[0]) \
                * math.sin(coord_2[0]) \
                - math.sin(coord_1[0]) \
                * math.cos(coord_2[0]) \
                * math.cos(coord_2[1] - coord_1[1])

            theta = math.atan2(y, x)

            bearing_array[index] = ((theta * 180) / math.pi + 360) % 360

        bearing_array[-1] = bearing_array[-2]

        return bearing_array

    def update_vehicle_position(self, incremental_distance):
        """

        Returns the closest coordinate to the current coordinate

        :param float incremental_distance: distance in m covered in the latest tick
        :returns: The new index of the vehicle
        :rtype: int
        """

        additional_distance = self.distance_remainder + incremental_distance

        # while the index of position can still be advanced
        while additional_distance > 0:
            # subtract contributions from every new index
            additional_distance = additional_distance - self.path_distances[self.current_index]

            # advance the index
            self.current_index = self.current_index + 1

        # backtrack a bit
        self.distance_remainder = additional_distance + self.path_distances[self.current_index - 1]
        self.current_index = self.current_index - 1

        return self.current_index

    @staticmethod
    def calculate_vector_square_magnitude(vector):
        """

        Calculate the square magnitude of an input vector. Must be one-dimensional.

        :param np.ndarray vector: NumPy array[N] representing a vector[N]
        :return: square magnitude of the input vector
        :rtype: float

        """

        return sum(i ** 2 for i in vector)

    @staticmethod
    def find_closest_coordinate_index(current_coord, path):
        """

        Returns the closest coordinate to current_coord in path

        :param np.ndarray current_coord: A NumPy array[N] representing a N-dimensional vector
        :param np.ndarray path: A NumPy array[M][N] of M coordinates which should be N-dimensional vectors
        :returns: index of the closest coordinate.
        :rtype: int

        """

        to_current_coord_from_path = np.abs(path - current_coord)
        distances_from_current_coord = np.zeros(len(to_current_coord_from_path))
        for i in range(len(to_current_coord_from_path)):
            # As we just need the minimum, using square magnitude will save performance
            distances_from_current_coord[i] = GIS.calculate_vector_square_magnitude(to_current_coord_from_path[i])

        return distances_from_current_coord.argmin()


if __name__ == "__main__":
    load_dotenv()
    google_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

    simulation_duration = 1 * 60 * 60

    origin_coord = np.array([38.9281815, -95.6770217])
    dest_coord = np.array([38.9282115, -95.6770268])
    waypoints = np.array([
        [38.9221906, -95.6762981],
        [38.9217086, -95.6767896], [38.9189926, -95.6753145], [38.9196768, -95.6724799],
        [38.9196768, -95.6724799], [38.9247448, -95.6714528], [38.9309102, -95.6749362],
        [38.928188, -95.6770129]
    ])

    locationSystem = GIS(api_key=google_api_key, origin_coord=origin_coord, dest_coord=dest_coord, waypoints=waypoints,
                         race_type="FSGP")

    locationSystem.tile_route(simulation_duration=simulation_duration)

    # path = locationSystem.get_path()
    # print(path)

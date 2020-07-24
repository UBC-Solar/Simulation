import requests
import json
import polyline
import numpy as np
import math
import os
from data.route.__init__ import route_directory
from simulation.common.helpers import timeit


class GIS:
    def __init__(self, api_key, origin_coord, dest_coord, waypoints):

        # Radius of the Earth in metres
        self.R = 6371009

        self.api_key = api_key

        self.current_index = 0
        self.distance_remainder = 0

        # path to file storing the route and elevation NumPy arrays
        route_file = route_directory / "route_data.npz"

        # if the file exists, load path from file
        if os.path.isfile(route_file):
            with np.load(route_file) as route_data:
                save_file_start_coord = route_data['origin_coord']
                save_file_end_coord = route_data['dest_coord']
                save_file_waypoints = route_data['waypoints']

                if (save_file_start_coord == origin_coord).all() and (save_file_end_coord == dest_coord).all() \
                        and (save_file_waypoints == waypoints).all():
                    print("Previous save file is being used...\n")
                    self.path = route_data['path']
                    self.path_elevations = route_data['elevations']
                    self.path_time_zones = route_data['time_zones']
                else:
                    print("New route requested. Calling Google API and creating new save file...\n")
                    self.path = self.update_path(origin_coord, dest_coord, waypoints)
                    self.path_elevations = self.calculate_path_elevations(self.path)
                    self.path_time_zones = self.calculate_time_zones(self.path)

                    with open(route_file, 'wb') as f:
                        np.savez(f, path=self.path, elevations=self.path_elevations, time_zones=self.path_time_zones,
                                 origin_coord=origin_coord,
                                 dest_coord=dest_coord, waypoints=waypoints)

        # otherwise call API and then save arrays to file
        else:
            print("Save file does not exist. Calling Google API and creating save file...\n")
            self.path = self.update_path(origin_coord, dest_coord, waypoints)
            self.path_elevations = self.calculate_path_elevations(self.path)
            self.path_time_zones = self.calculate_time_zones(self.path)

            with open(route_file, 'wb') as f:
                np.savez(f, path=self.path, elevations=self.path_elevations, time_zones=self.path_time_zones,
                         origin_coord=origin_coord,
                         dest_coord=dest_coord, waypoints=waypoints)

        self.path_distances = self.calculate_path_distances(self.path)
        self.path_gradients = self.calculate_path_gradients(self.path_elevations,
                                                            self.path_distances)

    def calculate_closest_gis_indices(self, cumulative_distances):
        """
        Takes in an array of point distances from starting point, returns a list of 
        self.path indices of coordinates which have a distance from the starting point
        closest to the point distances

        :param cumulative_distances: (float[N]) array of distances, where 
            cumulative_distances[x] > cumulative_distances[x-1]
        
        returns: (float[N]) array of indices of path
        """

        current_coordinate_index = 0
        next_coordinate_index = 1
        result = []

        # TODO: np.average the entire array rather than just slices
        for distance in np.nditer(cumulative_distances):
            if distance > np.average(self.path_distances[current_coordinate_index:next_coordinate_index + 1]):
                current_coordinate_index += 1
                next_coordinate_index += 1

            result.append(current_coordinate_index)

        return np.array(result)

    def calculate_time_zones(self, coords):
        """
        Takes in an array of coordinates, return the time zone relative to UTC, of each location in seconds

        :param coords: (float[N][lat lng]) array of coordinates

        returns: (float[N]) array of time differences in seconds
        """

        time_diff_temp = np.zeros(int(len(coords) / 625 + 1))

        for i in range(0, len(coords), 625):
            dummy_time = 1593604800
            url = f"https://maps.googleapis.com/maps/api/timezone/json?location={coords[i][0]},{coords[i][1]}&timestamp={dummy_time}&key={self.api_key}"

            r = requests.get(url)
            response = json.loads(r.text)

            time_diff_temp[int(i / 625)] = response['dstOffset'] + response['rawOffset']

        time_diff = np.repeat(time_diff_temp, 625)[0:len(coords)]

        return time_diff

    def get_time_zones(self, gis_indices):
        """
        Takes in an array of path indices, returns the time zone at each index

        :param gis_indices: (float[N]) array of path indices

        returns: (float[N]) array of time zones in seconds
        """

        return self.path_time_zones[gis_indices]

    def adjust_timestamps_to_local_times(self, timestamps, starting_drive_time, time_zones):
        """
        Takes in the timestamps of the vehicle's driving duration, starting drive time, and a list of time zones,
            returns the local times at each point

        :param timestamps: (int[N]) timestamps starting from 0, in seconds
        :param starting_drive_time: (int[N]) local time that the car was start to be driven in UNIX time (Daylight Saving included)
        :param time_zones: (int[N])
        """

        return timestamps + (starting_drive_time + time_zones[0]) + time_zones

    def get_gradients(self, gis_indices):
        """
        Takes in an array of path indices, returns the road gradient at each index

        :param gis_indices: (float[N]) array of path indices

        returns: (float[N]) array of road gradients
        """

        return self.path_gradients[gis_indices]

    # ----- Getters -----

    def get_path(self):
        """
        Returns all N coordinates of the path in a numpy array 
        [N][latitude, longitude]
        """

        return self.path

    def get_path_elevations(self):
        """
        Returns all N elevations of the path in a numpy array
        [N][elevation]
        """

        return self.path_elevations

    def get_path_distances(self):
        """
        Returns all N-1 distances of the path in a numpy array
        [N-1][elevation]
        """

        return self.path_distances

    def get_path_gradients(self):
        """
        Returns all N-1 gradients of a path in a numpy array
        [N-1][gradient]
        """

        return self.path_gradients

    # ----- Path calculation functions -----

    @timeit
    def update_path(self, origin_coord, dest_coord, waypoints):
        """
        Returns a path between the origin coordinate and the destination coordinate,
        passing through a group of optional waypoints.

        origin_coord: A numpy array [latitude, longitude] of the starting coordinate
        dest_coord: A numpy array [latitude, longitude] of the destination coordinate
        waypoint: A numpy array [n][latitude, longitude], where n<=10

        Returns: A numpy array [n][latitude, longitude], marking out the path.

        https://developers.google.com/maps/documentation/directions/start
        """

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

        url_end = f"&key={self.api_key}"

        url = url_head + url_waypoints + url_end

        print("url: {}".format(url))

        # HTTP GET
        r = requests.get(url)
        response = json.loads(r.text)

        path_points = []

        # If a route is found...
        if response['status'] == "OK":
            print("A route was found.")

            # Pick the first route in the list of available routes
            # A route consists of a series of legs
            for leg in response['routes'][0]['legs']:

                # Every leg contains an array of steps.
                for step in leg['steps']:
                    # every step contains an encoded polyline
                    polyline_raw = step['polyline']['points']
                    polyline_coords = polyline.decode(polyline_raw)
                    path_points = path_points + polyline_coords

        else:
            print(f"No route was found: {response['status']}")

        route = np.array(path_points)

        # Removes duplicate coordinates to prevent gradient calculation errors
        duplicate_coordinate_indices = np.where((np.diff(route[:, 0]) == 0)) and np.where((np.diff(route[:, 1]) == 0))
        route = np.delete(route, duplicate_coordinate_indices, axis=0)

        return route

    @timeit
    def calculate_path_elevations(self, coords):
        """
        Returns the elevations of every coordinate the array of coordinates passed in
            as a coordinate

        coords: A numpy array [n][latitude, longitude]

        Returns: A numpy array [n][elevation] in metres
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

        url_tail = "&key={}".format(self.api_key)

        # Get elevations
        elevations = np.zeros(len(coords))

        i = 0
        for location_string in location_strings:

            url = url_head + location_string + url_tail

            r = requests.get(url)
            response = json.loads(r.text)

            if response['status'] == "OK":

                for result in response['results']:
                    elevations[i] = result['elevation']
                    i = i + 1

            else:
                print("Error: No elevation was found")

        return elevations

    @timeit
    def calculate_path_distances(self, coords):
        """
        The coordinates are spaced quite tightly together, and they capture the
            features of the road. So, the lines between every pair of adjacent
            coordinates can be treated like a straight line, and the distances can
            thus be obtained.

        coords: A numpy array [n][latitude, longitude]

        Returns:
            - A numpy array [n-1][distances],
        """

        # TODO: can simplify this using np.diff()
        offset = np.roll(coords, (1, 1))

        # get the latitude and longitude differences, in radians
        diff = (coords - offset)[1:] * np.pi / 180
        diff_lat, diff_lng = np.split(diff, 2, axis=1)
        diff_lat = np.squeeze(diff_lat)
        diff_lng = np.squeeze(diff_lng)

        print(f"diff_lat: {diff_lat.shape}")
        print(f"diff_lng: {diff_lng.shape}")

        # get the mean latitude for every latitude, in radians
        mean_lat = ((coords + offset)[1:, 0] * np.pi / 180) / 2
        cosine_mean_lat = np.cos(mean_lat)

        print(f"cosine_mean_lat: {cosine_mean_lat.shape}")

        # multiply the latitude difference with the cosine_mean_latitude
        diff_lng_adjusted = cosine_mean_lat * diff_lng

        print(f"diff_lng_adjusted: {diff_lng_adjusted.shape}")

        # square, sum and square-root
        square_lat = np.square(diff_lat)
        square_lng = np.square(diff_lng_adjusted)
        square_sum = square_lat + square_lng

        path_distances = self.R * np.sqrt(square_sum)

        return path_distances

    @staticmethod
    @timeit
    def calculate_path_gradients(elevations, distances):
        """
        Get the approximate gradients of every point on the path.

        elevations: [N][elevations]
        distances: [N-1][distances]

        Returns:
            - gradients[N-1]

        Note:
            - gradient > 0 corresponds to uphill
            - gradient < 0 corresponds to downhill
        """

        # subtract every next elevation with the previous elevation to
        # get the difference in elevation
        # [1 2 3 4 5]
        # [5 1 2 3 4] -
        # -------------
        #   [1 1 1 1]

        # TODO: can simplify this using np.diff()
        offset = np.roll(elevations, 1)
        delta_elevations = (elevations - offset)[1:]

        # Divide the difference in elevation to get the gradient
        # gradient > 0: uphill
        # gradient < 0: downhill

        gradients = delta_elevations / distances

        return gradients

    def calculate_current_elevation(self):
        """
        Get the elevation of the closest point to the current point
        """

        return self.path_elevations[self.current_index]

    def calculate_current_gradient(self):
        """
        Get the gradient of the point closest to the current location
        """

        return self.path_gradients[self.current_index]

    def calculate_current_heading(self):
        """
        From the current and previous coordinate, calculate the current bearing of the vehicle.
            This is also the azimuth angle of the vehicle
        """

        if self.current_index - 1 < 0:
            coord_1 = self.path[self.current_index + 1]
            coord_2 = self.path[self.current_index]
        else:
            coord_1 = self.path[self.current_index]
            coord_2 = self.path[self.current_index - 1]

        y = math.sin(math.radians(coord_2[1] - coord_1[1])) * \
            math.cos(math.radians(coord_2[0]))

        x = math.cos(math.radians(coord_1[0])) * \
            math.sin(math.radians(coord_2[0])) - \
            math.sin(math.radians(coord_1[0])) * \
            math.sin(math.radians(coord_2[0])) * \
            math.cos(math.radians(coord_2[1] - coord_1[0]))

        theta = math.atan2(y, x)

        bearing = ((theta * 180) / math.pi + 360) % 360

        return bearing

    def update_vehicle_position(self, incremental_distance):
        """
        Returns the closest coordinate to the current coordinate

        incremental_distance: distance in m covered in the latest tick

        Returns: The new index of the vehicle
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


if __name__ == "__main__":
    google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"

    origin_coord = np.array([39.0918, -94.4172])

    waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

    dest_coord = np.array([43.6142, -116.2080])

    locationSystem = GIS(api_key=google_api_key, origin_coord=origin_coord, dest_coord=dest_coord, waypoints=waypoints)

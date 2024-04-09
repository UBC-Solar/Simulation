"""
A class to extract local and path weather predictions such as wind_speed, 
    wind_direction, cloud_cover and weather type
"""
import numpy as np
import os
import logging

from simulation.cache.weather import weather_directory
from simulation.model.environment.weather_forecasts.base_weather_forecasts import BaseWeatherForecasts
from simulation.common import helpers, constants

import core


class WeatherForecasts(BaseWeatherForecasts):
    """
    Class that gathers weather data and performs calculations on it to allow the implementation of weather phenomenon
    such as changes in wind speeds and cloud cover in the simulation.

    Attributes:
        coords (NumPy array [N][lat, long]): a list of N coordinates for which to gather weather forecasts for
        origin_coord (NumPy array [lat, long]): the starting coordinate
        dest_coord (NumPy array [lat, long]): the ending coordinate
        last_updated_time (int): value that tells us the starting time after which we have weather data available

        weather_forecast (NumPy array [N][T][9]): array that stores the complete weather forecast data. N represents the
            number of coordinates, T represents time length which differs depending on the `weather_data_frequency`
            argument ("current" -> T = 1 ; "hourly" -> T = 24 ; "daily" -> T = 8). The last 9 represents the number of
            weather forecast fields available. These are: (latitude, longitude, dt (UNIX time), timezone_offset
            (in seconds), dt + timezone_offset (local time), wind_speed, wind_direction, cloud_cover, description_id)
    """

    def __init__(self, coords, race_type, provider: str, origin_coord=None, hash_key=None):

        """

        Initializes the instance of a WeatherForecast class

        :param origin_coord: A NumPy array of a single [latitude, longitude]
        :param str provider: string indicating weather provider
        :param coords: A NumPy array of [latitude, longitude]
        :param hash_key: key used to identify cached data as valid for a Simulation model

        """
        self.race_type = race_type
        self.last_updated_time = -1

        if origin_coord is not None:
            self.origin_coord = np.array(origin_coord)
        else:
            self.origin_coord = coords[0]
        self.dest_coord = coords[-1]

        assert race_type in ["ASC", "FSGP"]

        if self.race_type == "ASC":
            self.coords = coords[::constants.REDUCTION_FACTOR]
            weather_file = weather_directory / f"weather_data_{provider}.npz"
        else:
            self.coords = np.array([coords[0], coords[-1]])
            weather_file = weather_directory / f"weather_data_FSGP_{provider}.npz"

        # if the file exists, load path from file
        print(f"Expecting: {weather_file}")
        if os.path.isfile(weather_file):
            print("Here?")
            with np.load(weather_file) as weather_data:
                if weather_data['hash'] == hash_key:

                    print("Previous weather save file is being used...\n")

                    self.weather_forecast = weather_data['weather_forecast']

                    start_time_unix = self.weather_forecast[0, 0, 2]
                    end_time_unix = self.weather_forecast[0, -1, 2]
                    start_time = helpers.date_from_unix_timestamp(start_time_unix)
                    end_time = helpers.date_from_unix_timestamp(end_time_unix)

                    print("----- Weather save file information -----\n")
                    print(f"--- Data time range ---")
                    print(f"Start time (UTC)f: {start_time} [{start_time_unix:.0f}]\n"
                          f"End time (UTC): {end_time} [{end_time_unix:.0f}]\n")

                    print("--- Array information ---")
                    for key in weather_data:
                        print(f"> {key}: {weather_data[key].shape}")
        else:
            logging.error("Update API cache by calling CacheAPI.py\nExiting simulation...")
            exit()

        self.last_updated_time = self.weather_forecast[0, 0, 2]

    def calculate_closest_weather_indices(self, cumulative_distances):
        """

        :param np.ndarray cumulative_distances: NumPy Array representing cumulative distances theoretically achievable for a given input speed array
        :returns: array of the closest weather indices.
        :rtype: np.ndarray

        """

        """
        IMPORTANT: we only have weather coordinates for a discrete set of coordinates. However, the car could be at any
        coordinate in between these available weather coordinates. We need to figure out what coordinate the car is at
        at each timestep and then we can figure out the full weather forecast at each timestep.

        For example, imagine the car is at some coordinate (10, 20). Further imagine that we have a week's worth of
        weather forecasts for the following five coordinates: (5, 4), (11, 19), (20, 30), (40, 30), (0, 60). Which
        set of weather forecasts should we choose? Well, we should choose the (11, 19) one since our coordinate
        (10, 20) is closest to (11, 19). This is what the following code is accomplishing. However, it is not dealing
        with the coordinates directly but rather is dealing with the distances between the coordinates. 

        Furthermore, once we have chosen a week's worth of weather forecasts for a specific coordinate, we must isolate
        a single weather forecast depending on what time the car is at the coordinate (10, 20). That is the job of the
        `get_weather_forecast_in_time()` method.
        
        """

        # if racing FSGP, there is no need for distance calculations. We will return only the origin coordinate
        # This characterizes the weather at every point along the FSGP tracks
        # with the weather at a single coordinate on the track, which is great for reducing the API calls and is a
        # reasonable assumption to make for FSGP only.
        if self.race_type == "FSGP":
            result = np.zeros_like(cumulative_distances, dtype=int)
            return result

        # a list of all the coordinates that we have weather data for
        weather_coords = self.weather_forecast[:, 0, 0:2]

        # distances between all the coordinates that we have weather data for
        weather_path_distances = helpers.calculate_path_distances(weather_coords)
        cumulative_weather_path_distances = np.cumsum(weather_path_distances)

        # makes every even-index element negative, this allows the use of np.diff() to calculate the sum of consecutive
        # elements
        cumulative_weather_path_distances[::2] *= -1

        # contains the average distance between two consecutive elements in the cumulative_weather_path_distances array
        average_distances = np.abs(np.diff(cumulative_weather_path_distances) / 2)

        return core.closest_weather_indices_loop(cumulative_distances, average_distances)

    @staticmethod
    def _python_calculate_closest_weather_indices(cumulative_distances, average_distances):
        """

        Python implementation of calculate_closest_weather_indices. See parent function for documentation details.

        """

        current_coordinate_index = 0
        result = []

        for distance in np.nditer(cumulative_distances):

            # makes sure the current_coordinate_index does not exceed its maximum value
            if current_coordinate_index > len(average_distances) - 1:
                current_coordinate_index = len(average_distances) - 1

            if distance > average_distances[current_coordinate_index]:
                current_coordinate_index += 1
                if current_coordinate_index > len(average_distances) - 1:
                    current_coordinate_index = len(average_distances) - 1

            result.append(current_coordinate_index)

        return np.array(result)

    @staticmethod
    def _python_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array):
        """

        Python implementation to find the indices of the closest timestamps in dt_local_array and package them into a NumPy Array

        :param np.ndarray unix_timestamps: NumPy Array (float[N]) of unix timestamps of the vehicle's journey
        :param np.ndarray dt_local_array: NumPy Array (float[N]) of local times, represented as unix timestamps
        :returns: NumPy Array of (int[N]) containing closest timestamp indices used by get_weather_forecast_in_time
        :rtype: np.ndarray

        """
        closest_time_stamp_indices = []
        for unix_timestamp in unix_timestamps:
            unix_timestamp_array = np.full_like(dt_local_array, fill_value=unix_timestamp)
            differences = np.abs(unix_timestamp_array - dt_local_array)
            minimum_index = np.argmin(differences)
            closest_time_stamp_indices.append(minimum_index)

        return np.asarray(closest_time_stamp_indices, dtype=np.int32)

    def get_weather_forecast_in_time(self, indices, unix_timestamps):
        """

        Takes in an array of indices of the weather_forecast array, and an array of timestamps. Uses those to figure out
        what the weather forecast is at each time step being simulated.

        we only have weather at discrete timestamps. The car however can be in any timestamp in
        between. Therefore, we must be able to choose the weather timestamp that is closest to the one that the car is in
        so that we can more accurately determine the weather experienced by the car at that timestamp.

        For example, imagine the car is at some coordinate (x,y) at timestamp 100. Imagine we know the weather forecast
        at (x,y) for five different timestamps: 0, 30, 60, 90, and 120. Which weather forecast should we
        choose? Clearly, we should choose the weather forecast at 90 since it is the closest to 100. That's what the
        below code is accomplishing.

        :param np.ndarray indices: (int[N]) coordinate indices of self.weather_forecast
        :param np.ndarray unix_timestamps: (int[N]) unix timestamps of the vehicle's journey
        :returns:
            - A NumPy array of size [N][9]
            - [9] (latitude, longitude, unix_time, timezone_offset, unix_time_corrected, wind_speed, wind_direction,
                        cloud_cover, precipitation, description):
        :rtype: np.ndarray

        """

        return core.weather_in_time(unix_timestamps.astype(np.int64), indices.astype(np.int64), self.weather_forecast)

    def _python_get_weather_in_time(self, unix_timestamps, indices):
        full_weather_forecast_at_coords = self.weather_forecast[indices]
        dt_local_array = full_weather_forecast_at_coords[0, :, 4]

        temp_0 = np.arange(0, full_weather_forecast_at_coords.shape[0])
        closest_timestamp_indices = self._python_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array)

        return full_weather_forecast_at_coords[temp_0, closest_timestamp_indices]

    @staticmethod
    def _get_array_directional_wind_speed(vehicle_bearings, wind_speeds, wind_directions):
        """

        Returns the array of wind speed in m/s, in the direction opposite to the 
            bearing of the vehicle


        :param np.ndarray vehicle_bearings: (float[N]) The azimuth angles that the vehicle in, in degrees
        :param np.ndarray wind_speeds: (float[N]) The absolute speeds in m/s
        :param np.ndarray wind_directions: (float[N]) The wind direction in the meteorlogical convention. To convert from meteorlogical convention to azimuth angle, use (x + 180) % 360
        :returns: The wind speeds in the direction opposite to the bearing of the vehicle
        :rtype: np.ndarray
        
        """

        # wind direction is 90 degrees meteorological, so it is 270 degrees azimuthal. car is 90 degrees
        #   cos(90 - 90) = cos(0) = 1. Wind speed is moving opposite to the car,
        # car is 270 degrees, cos(90-270) = -1. Wind speed is in direction of the car.
        return wind_speeds * (np.cos(np.radians(wind_directions - vehicle_bearings)))

    @staticmethod
    def _get_weather_advisory(weather_id):
        """

        Returns a string indicating the type of weather to expect, from the standardized
            weather code passed as a parameter

        https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2
        :param int weather_id: Weather ID
        :return: type of weather advisory
        :rtype: str

        """

        if 200 <= weather_id < 300:
            return "Thunderstorm"
        elif 300 <= weather_id < 500:
            return "Drizzle"
        elif 500 <= weather_id < 600:
            return "Rain"
        elif 600 <= weather_id < 700:
            return "Snow"
        elif weather_id == 800:
            return "Clear"
        else:
            return "Unknown"


if __name__ == "__main__":
    pass

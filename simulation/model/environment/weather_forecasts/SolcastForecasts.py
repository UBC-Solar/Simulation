"""
A class to extract local and path weather predictions such as wind_speed, 
    wind_direction, cloud_cover and weather type using data from Solcast.
"""
import numpy as np
import os
import logging

from simulation.model.environment.weather_forecasts import BaseWeatherForecasts
from simulation.model.environment import SolcastEnvironment
from simulation.common import helpers, constants, Race

import core


class SolcastForecasts(BaseWeatherForecasts):
    """
    Class that gathers weather data and performs calculations on it to allow the implementation of weather phenomenon
    such as changes in wind speeds and cloud cover in the simulation.

    Attributes:
        coords (NumPy array [N][lat, long]): a list of N coordinates for which to gather weather forecasts for
        origin_coord (NumPy array [lat, long]): the starting coordinate
        dest_coord (NumPy array [lat, long]): the ending coordinate
        last_updated_time (int): value that tells us the starting time after which we have weather data available

        weather_forecast (NumPy array [N][T][6]): array that stores the complete weather forecast data. N represents the
            number of coordinates, T represents time length with temporal granularity defined in settings_*.json.
            The last 6 represents the number of weather forecast fields available. These are: time_dt (UTC UNIX time),
            latitude, longitude, wind_speed (m/s), wind_direction (meteorological convention), ghi (W/m^2)
    """

    def __init__(self, coords, race: Race, origin_coord=None, hash_key=None):

        """

        Initializes the instance of a WeatherForecast class

        :param origin_coord: A NumPy array of a single [latitude, longitude]
        :param str provider: string indicating weather provider
        :param coords: A NumPy array of [latitude, longitude]
        :param hash_key: key used to identify cached data as valid for a Simulation model

        """
        super().__init__(coords, race, "SOLCAST", origin_coord, hash_key)
        self.race = race
        self.last_updated_time = self.weather_forecast[0, 0, 0]

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
        if self.race.race_type == Race.FSGP:
            result = np.zeros_like(cumulative_distances, dtype=int)
            return result

        # a list of all the coordinates that we have weather data for
        weather_coords = self.weather_forecast[:, 0, 1:3]

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

    def get_weather_forecast_in_time(self, indices, unix_timestamps, start_time, tick) -> SolcastEnvironment:
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
        :param int start_time: time since the start of the race that simulation is beginning
        :param int tick: length of a tick in seconds
        :returns: a SolcastEnvironment object with time_dt, latitude, longitude, wind_speed, wind_direction, and ghi.
        :rtype: SolcastEnvironment
        """
        forecasts_array = core.weather_in_time(unix_timestamps.astype(np.int64), indices.astype(np.int64), self.weather_forecast, 0)

        # roll_by_tick = int(3600 / tick) * helpers.hour_from_unix_timestamp(forecasts_array[0, 0])
        # forecasts_array = np.roll(forecasts_array, -roll_by_tick, 0)

        weather_object = SolcastEnvironment()

        weather_object.time_dt = forecasts_array[:, 0]
        weather_object.latitude = forecasts_array[:, 1]
        weather_object.longitude = forecasts_array[:, 2]
        weather_object.wind_speed = forecasts_array[:, 3]
        weather_object.wind_direction = forecasts_array[:, 4]
        weather_object.ghi = forecasts_array[:, 5]

        return weather_object

    def _python_get_weather_in_time(self, unix_timestamps, indices):
        full_weather_forecast_at_coords = self.weather_forecast[indices]
        dt_local_array = full_weather_forecast_at_coords[0, :, 0]

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


if __name__ == "__main__":
    pass

"""
A class to extract local and path weather predictions such as wind_speed, 
    wind_direction, cloud_cover and weather type
"""
import json
import numpy as np
import os
import pathlib
import requests
import sys
from simulation.data.weather import weather_directory
from simulation.common import helpers
from tqdm import tqdm


class WeatherForecasts:
    """
    Class that gathers weather data and performs calculations on it to allow the implementation of weather phenomenon
    such as changes in wind speeds and cloud cover in the simulation.

    Attributes:
        api_key (string): key that allows us to gather data from OpenWeatherAPI
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

    def __init__(self, api_key, coords, duration, race_type, weather_data_frequency="daily", force_update=False):
        """
        Initializes the instance of a WeatherForecast class

        :param api_key: A personal OpenWeatherAPI key to access weather forecasts
        :param coords: A NumPy array of [latitude, longitude]
        :param weather_data_frequency: Influences what resolution weather data is requested, must be one of
            "current", "hourly", or "daily"
        :param duration: amount of time simulated (in hours)
        :param force_update: if true, weather cache data is updated by calling the OpenWeatherAPI
        """
        self.race_type = race_type
        self.api_key = api_key
        self.last_updated_time = -1

        # Setup for Golang use in get_weather_forecast_in_time()
        go_directory = pathlib.Path(__file__).parent

        # self.lib = ctypes.cdll.LoadLibrary(f"{go_directory}/weather_in_time_loop.so")
        # self.lib.weather_in_time_loop.argtypes = [
        #     ctypes.POINTER(ctypes.c_double),
        #     ctypes.POINTER(ctypes.c_double),
        #     ctypes.POINTER(ctypes.c_double),
        #     ctypes.c_longlong,
        #     ctypes.c_longlong
        # ]

        self.origin_coord = coords[0]
        self.dest_coord = coords[-1]

        assert race_type in ["ASC", "FSGP"]

        if self.race_type == "ASC":
            self.coords = self.cull_dataset(coords, reduction_factor=625)
            weather_file = weather_directory / "weather_data.npz"
        else:
            self.coords = np.array([coords[0], coords[-1]])
            weather_file = weather_directory / "weather_data_FSGP.npz"

        api_call_required = True

        # if the file exists, load path from file
        if os.path.isfile(weather_file) and force_update is False:
            with np.load(weather_file) as weather_data:
                if np.array_equal(weather_data['origin_coord'], self.origin_coord) and \
                        np.array_equal(weather_data['dest_coord'], self.dest_coord):

                    api_call_required = False

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
                    print()

        if api_call_required or force_update:
            print("Different weather data requested and/or weather file does not exist. "
                  "Calling OpenWeather API and creating weather save file...\n")
            self.weather_forecast = self.update_path_weather_forecast(self.coords, weather_data_frequency, duration)

            with open(weather_file, 'wb') as f:
                np.savez(f, weather_forecast=self.weather_forecast, origin_coord=self.origin_coord,
                         dest_coord=self.dest_coord)

        self.last_updated_time = self.weather_forecast[0, 0, 2]

    def get_coord_weather_forecast(self, coord, weather_data_frequency, duration):
        """
        Passes in a single coordinate, returns a weather forecast
        for the coordinate depending on the entered "weather_data_frequency"
        argument. This function is unlikely to ever be called directly.

        :param coord: A single coordinate stored inside a NumPy array [latitude, longitude]
        :param weather_data_frequency: Influences what resolution weather data is requested, must be one of
            "current", "hourly", or "daily"
        :param duration: amount of time simulated (in hours)

        :returns weather_array: [N][9]
        - [N]: is 1 for "current", 24 for "hourly", 8 for "daily"
        - [9]: (latitude, longitude, dt (UNIX time), timezone_offset (in seconds), dt + timezone_offset (local time),
               wind_speed, wind_direction, cloud_cover, description_id)

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
              f"&exclude=minutely,{exclude_string}&appid={self.api_key}"

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
                  f"&exclude=minutely,hourly,current&appid={self.api_key}"

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

    def update_path_weather_forecast(self, coords, weather_data_frequency, duration):
        """
        Passes in a list of coordinates, returns the hourly weather forecast
        for each of the coordinates
        
        :param coords: A NumPy array of [coord_index][2]
        - [2] => [latitude, longitude]
        :param weather_data_frequency: Influences what resolution weather data is requested, must be one of
            "current", "hourly", or "daily"
        :param duration: duration of weather requested, in hours

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
                weather_forecast[i] = self.get_coord_weather_forecast(coord, weather_data_frequency, int(duration))
                pbar.update(1)
        print()

        return weather_forecast

    def calculate_closest_weather_indices(self, cumulative_distances):
        """

        Args:
            cumulative_distances: NumPy Array representing cumulative distances theoretically achievable for a given input speed array

        Returns:

        """
        current_coordinate_index = 0
        result = []

        # TODO: can rewrite this to use self.gis.path[closest_gis_indices]

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

    def golang_calculate_closest_timestamp_indices(self, unix_timestamps, dt_local_array):
        """
        GoLang implementation to find the indices of the closest timestamps in dt_local_array and package them into a NumPy Array

        Args:
            unix_timestamps: NumPy Array (float[N]) unix timestamps of the vehicle's journey
            dt_local_array: NumPy Array (float[N]) local times, represented as unix timestamps

        Returns: NumPy Array (int[N]) containing closest timestamp indices used by get_weather_forecast_in_time

        """
        unix_timestamps_pointer, closest_time_stamp_indices_pointer, \
        closest_time_stamp_indices = helpers.generate_golang_io_pointers(unix_timestamps)

        dt_local_arr_pointer, _, _ = helpers.generate_golang_io_pointers(dt_local_array)

        self.lib.weather_in_time_loop(
            unix_timestamps_pointer,
            closest_time_stamp_indices_pointer,
            dt_local_arr_pointer,
            len(dt_local_array),
            len(unix_timestamps))

        return np.array(closest_time_stamp_indices, 'i')

    @staticmethod
    def python_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array):
        """

        Python implementation to find the indices of the closest timestamps in dt_local_array and package them into a NumPy Array

        Args:
            unix_timestamps: NumPy Array (float[N]) of unix timestamps of the vehicle's journey
            dt_local_array: NumPy Array (float[N]) of local times, represented as unix timestamps

        Returns: NumPy Array of (int[N]) containing closest timestamp indices used by get_weather_forecast_in_time

        """
        closest_time_stamp_indices = []
        for unix_timestamp in unix_timestamps:
            unix_timestamp_array = np.full_like(dt_local_array, fill_value=unix_timestamp)
            differences = np.abs(unix_timestamp_array - dt_local_array)
            minimum_index = np.argmin(differences)
            closest_time_stamp_indices.append(minimum_index)

        return np.asarray(closest_time_stamp_indices, dtype=np.int32)

    @helpers.timeit
    def get_weather_forecast_in_time(self, indices, unix_timestamps, golang=False):
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

        :param indices: (int[N]) coordinate indices of self.weather_forecast
        :param unix_timestamps: (int[N]) unix timestamps of the vehicle's journey
        :param golang: Boolean specifying whether a GoLang implementation of get_weather_forecast_in_time should be used
                   If false, a slower Python implementation is used.

        :returns
        - A NumPy array of size [N][9]
        - [9]: (latitude, longitude, unix_time, timezone_offset, unix_time_corrected, wind_speed, wind_direction,
                    cloud_cover, precipitation, description):

        """

        # each element is the weather forecast for all available times at that coordinate
        full_weather_forecast_at_coords = self.weather_forecast[indices]
        dt_local_array = full_weather_forecast_at_coords[0, :, 4]

        if golang:
            closest_timestamp_indices = self.golang_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array)
        else:
            closest_timestamp_indices = self.python_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array)

        temp_0 = np.arange(0, full_weather_forecast_at_coords.shape[0])

        # if you're wondering why or how this works, don't ask because I don't know, it just does
        # this is what duct-taping looks like in software engineering
        result = full_weather_forecast_at_coords[tuple((temp_0, closest_timestamp_indices))]

        return result

    @staticmethod
    def cull_dataset(coords, reduction_factor):
        """
        As we currently have a limited number of API calls(60) every minute with the
            current Weather API, we must shrink the dataset significantly. As the
            OpenWeatherAPI models have a resolution of between 2.5 - 70 km, we will
            go for a resolution of 25km. Assuming we travel at 100km/h for 12 hours,
            1200 kilometres/25 = 48 API calls

        As the Google Maps API has a resolution of around 40m between points,
            for ASC, we must cull at 625:1 (because 25,000m / 40m = 625)
        """

        return coords[::reduction_factor]

    @staticmethod
    def get_array_directional_wind_speed(vehicle_bearings, wind_speeds, wind_directions):
        """
        Returns the array of wind speed in m/s, in the direction opposite to the 
            bearing of the vehicle


        vehicle_bearings: (float[N]) The azimuth angles that the vehicle in, in degrees
        wind_speeds: (float[N]) The absolute speeds in m/s
        wind_directions: (float[N]) The wind direction in the meteorlogical convention. To convert from
            meteorlogical convention to azimuth angle, use (x + 180) % 360

        Returns: The wind speeds in the direction opposite to the bearing of the vehicle
        """

        # wind direction is 90 degrees meteorlogical, so it is 270 degrees azimuthal. car is 90 degrees
        #   cos(90 - 90) = cos(0) = 1. Wind speed is moving opposite to the car,
        # car is 270 degrees, cos(90-270) = -1. Wind speed is in direction of the car.
        return wind_speeds * (np.cos(np.radians(wind_directions - vehicle_bearings)))

    @staticmethod
    def get_weather_advisory(weather_id):
        """
        Returns a string indicating the type of weather to expect, from the standardized
            weather code passed as a parameter

        https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2
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

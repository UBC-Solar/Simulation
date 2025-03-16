import os
import json
import requests
import numpy as np
from simulation.config import SolcastConfig, OpenweatherConfig, OpenweatherPeriod, EnvironmentConfig, CompetitionConfig
from numpy.typing import NDArray, ArrayLike
from simulation.race import Coordinate
from simulation.query import Query
from dotenv import load_dotenv


load_dotenv()


class SolcastQuery(Query[SolcastConfig]):
    def __init__(self, config: EnvironmentConfig):
        super().__init__(config)
        self._competition_config: CompetitionConfig = self._config.competition_config
        self._weather_query_config: OpenweatherConfig = self._config.weather_query_config

    def make(self):
        raise NotImplementedError("Querying for Solcast was not re-implemented when querying was refactored. See "
                                  "https://github.com/UBC-Solar/Simulation/blob"
                                  "/d33fa563b5feb09585af1db57be60a031964edc8/simulation/utils/Query.py for "
                                  "inspiration on re-implementation.")


class OpenweatherQuery(Query[OpenweatherConfig]):
    def __init__(self, config: EnvironmentConfig):
        super().__init__(config)
        self._competition_config: CompetitionConfig = self._config.competition_config
        self._weather_query_config: OpenweatherConfig = self._config.weather_query_config

    def make(self) -> NDArray:
        num_days = self._competition_config.duration
        simulation_duration = num_days * 24  # Duration of simulation in hours

        coords = self._competition_config.route_config.coordinates
        forecast_period: OpenweatherPeriod = self._weather_query_config.weather_period

        weather_forecast = self.update_path_weather_forecast_openweather(coords,
                                                                         forecast_period,
                                                                         simulation_duration)

        return weather_forecast

    @staticmethod
    def update_path_weather_forecast_openweather(coords: ArrayLike, weather_period: OpenweatherPeriod, duration: int):
        """

        Passes in a list of coordinates, returns the hourly weather forecast
        for each of the coordinates

        :param ArrayLike coords: An array of coordinates that the weather will be forecasted for
        :param OpenweatherPeriod weather_period: The period of each forecast (how much "time" they represent)
        :param int duration: duration of weather requested, in hours

        :returns
        - A NumPy array [coord_index][N][9]
        - [coord_index]: the index of the coordinates passed into the function
        - [N]: is 1 for "current", 24 for "hourly", 8 for "daily"
        - [9]: (latitude, longitude, dt (UNIX time), timezone_offset (in seconds), dt + timezone_offset (local time),
               wind_speed, wind_direction, cloud_cover, description_id)

        """
        time_length = {"Current": 1, "Daily": 8}
        if int(duration) > 48 and weather_period == OpenweatherPeriod.Hourly:
            time_length.update({"Hourly": 54})
        else:
            time_length.update({"Hourly": 48})

        shape = (len(coords), time_length[str(weather_period)], 9)
        weather_forecast = np.zeros(shape)

        def get_weather_forecast_for_coord(coord: Coordinate):
            return OpenweatherQuery.get_coord_weather_forecast_openweather(
                coord,
                weather_period,
                duration
            )

        weather_forecast[:] = [get_weather_forecast_for_coord(coord) for coord in coords]

        return weather_forecast

    @staticmethod
    def get_coord_weather_forecast_openweather(coord: Coordinate, weather_period: OpenweatherPeriod, duration: int):
        """

        Passes in a single coordinate, returns a weather forecast
        for the coordinate depending on the entered "weather_data_frequency"
        argument. This function is unlikely to ever be called directly.

        :param Coordinate coord: A coordinate that the weather will be forecasted for
        :param OpenweatherPeriod weather_period: The period of each forecast (how much "time" they represent)
        :param int duration: duration of weather requested, in hours

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

        weather_periods: list[str] = [period for period in OpenweatherPeriod]
        weather_periods.remove(weather_period)

        exclude_string = ",".join(weather_periods).lower()

        url = f"https://api.openweathermap.org/data/3.0/onecall?lat={coord[0]}&lon={coord[1]}" \
              f"&exclude=minutely,{exclude_string}&appid={os.environ['OPENWEATHER_API_KEY']}"

        # ----- Calling OpenWeatherAPI ------

        r = requests.get(url)
        response = json.loads(r.text)

        # ----- Processing API response -----

        # Ensures that response[weather_data_frequency] is always a list of dictionaries
        weather_period_str = str(weather_period).lower()
        if isinstance(response[weather_period_str], dict):
            weather_data_list = [response[weather_period_str]]
        else:
            weather_data_list = response[weather_period_str]

        # If the weather data is too long, then append the daily requests as well.
        if weather_period == "Hourly" and duration > 24:

            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={coord[0]}&lon={coord[1]}" \
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

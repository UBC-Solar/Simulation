import functools
from abc import ABC, abstractmethod

import dill
import numpy as np
from simulation.common import Race, constants, helpers
from simulation.cache.weather import weather_directory
import logging
import os


class BaseWeatherForecasts(ABC):
    def __init__(self, coords, race: Race, provider: str, origin_coord=None, hash_key=None):
        self.race = race

        if origin_coord is not None:
            self.origin_coord = np.array(origin_coord)
        else:
            self.origin_coord = coords[0]
        self.dest_coord = coords[-1]

        if self.race.race_type == Race.ASC:
            self.coords = coords[::constants.REDUCTION_FACTOR]
            weather_file = weather_directory / f"weather_data_{provider}.npz"
        elif self.race.race_type == Race.FSGP:
            self.coords = np.array([coords[0], coords[-1]])
            weather_file = weather_directory / f"weather_data_FSGP_{provider}.npz"
        else:
            raise ValueError(f"base_weather_forecasts has not implemented retrieving race {repr(self.race.race_type)}")

        # if the file exists, load path from file
        if os.path.isfile(weather_file):
            if provider == "SOLCAST":
                with open(weather_file, 'rb') as file:
                    weather_data = dill.load(file)
            elif provider == "OPENWEATHER":
                weather_data = np.load(weather_file)
            else:
                raise ValueError(f"base_weather_forecasts has not implemented retrieving provider {provider}")

            if weather_data['hash'] == hash_key:

                print("Previous weather save file is being used...\n")

                self.weather_forecast = weather_data['weather_forecast']

        else:
            logging.error("Get or update cached weather data by invoking cache_data.py\nExiting simulation...")
            exit()

    @abstractmethod
    def calculate_closest_weather_indices(self, cumulative_distances) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def get_weather_forecast_in_time(self, indices, unix_timestamps, start_hour, tick) -> np.ndarray:
        raise NotImplementedError


class WeatherData:
    def __init__(self):
        self._time_dt = None
        self._latitude = None
        self._longitude = None
        self._wind_speed = None
        self._wind_direction = None
        self._ghi = None

    @property
    def time_dt(self):
        if (value := self._time_dt) is not None:
            return value
        else:
            raise ValueError("time_dt is None!")

    @time_dt.setter
    def time_dt(self, value):
        self._time_dt = value

    @property
    def latitude(self):
        if (value := self._latitude) is not None:
            return value
        else:
            raise ValueError("latitude is None!")

    @latitude.setter
    def latitude(self, value):
        self._latitude = value

    @property
    def longitude(self):
        if (value := self._longitude) is not None:
            return value
        else:
            raise ValueError("longitude is None!")

    @longitude.setter
    def longitude(self, value):
        self._longitude = value

    @property
    def wind_speed(self):
        if (value := self._wind_speed) is not None:
            return value
        else:
            raise ValueError("wind_speed is None!")

    @wind_speed.setter
    def wind_speed(self, value):
        self._wind_speed = value

    @property
    def wind_direction(self):
        if (value := self._wind_direction) is not None:
            return value
        else:
            raise ValueError("wind_direction is None!")

    @wind_direction.setter
    def wind_direction(self, value):
        self._wind_direction = value

    @property
    def ghi(self):
        if (value := self._ghi) is not None:
            return value
        else:
            raise ValueError("ghi is None!")

    @ghi.setter
    def ghi(self, value):
        self._ghi = value








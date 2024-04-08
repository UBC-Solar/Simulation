from abc import ABC, abstractmethod
import numpy as np


class BaseWeatherForecasts(ABC):
    @abstractmethod
    def calculate_closest_weather_indices(self, cumulative_distances) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def get_weather_forecast_in_time(self, indices, unix_timestamps) -> np.ndarray:
        raise NotImplementedError


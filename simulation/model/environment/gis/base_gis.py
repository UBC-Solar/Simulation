from abc import ABC, abstractmethod
import numpy as np


class BaseGIS(ABC):
    @abstractmethod
    def calculate_closest_gis_indices(self, cumulative_distances) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def get_path_elevations(self) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def get_gradients(self, gis_indices) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def get_time_zones(self, gis_indices) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def get_path(self) -> np.ndarray:
        raise NotImplementedError

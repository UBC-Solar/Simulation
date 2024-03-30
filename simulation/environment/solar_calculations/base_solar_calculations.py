from abc import ABC, abstractmethod
import numpy as np


class BaseSolarCalculations(ABC):
    @abstractmethod
    def get_solar_irradiance(self, coords, time_zones, local_times,
                             elevations, cloud_covers) -> np.ndarray:
        raise NotImplementedError
from abc import ABC, abstractmethod
import numpy as np


class BaseSolarCalculations(ABC):
    @abstractmethod
    def calculate_array_GHI(self, coords, time_zones, local_times,
                             elevations, cloud_covers) -> np.ndarray:
        raise NotImplementedError
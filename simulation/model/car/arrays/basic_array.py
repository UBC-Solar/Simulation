import numpy as np

from simulation.model.car.arrays.base_array import BaseArray
from simulation.common import BrightSide


class BasicArray(BaseArray):

    # incident_sunlight:
    def __init__(self):
        super().__init__()

        # solar cell efficiency
        self.panel_efficiency = BrightSide.panel_efficiency

        # solar panel size in m^2
        self.panel_size = BrightSide.panel_size

        # please do not use this.
        self.solar_irradiance = 1200

    def calculate_produced_energy(self, solar_irradiance, tick, parameters = None):
        """

        Returns a numpy array with the energy produced by the solar panels across
        each the length of each tick

        :param np.ndarray solar_irradiance: (float[N]) the global horizontal irradiance(GHI) at
            each moment experienced by the vehicle, in W/m2
        :param float tick: (float) the duration of a time step in seconds

        :returns: (float[N]) array of energy produced by the solar panels on the vehicle
            in Joules
        :rtype: np.ndarray

        """
        if parameters is None:
            parameters = self.parameters

        produced_energy = solar_irradiance * self.panel_efficiency * self.panel_size * tick
        produced_energy *= np.polyval([parameters[0], parameters[1]], produced_energy)

        return produced_energy

    def __str__(self):
        return(f"BasicArray: incident_sunlight: {self.solar_irradiance}W/m^2\n"
               f"BasicArray: panel_size: {self.panel_size}m^2\n"
               f"BasicArray: panel_efficiency: {self.panel_efficiency * 100}%\n")

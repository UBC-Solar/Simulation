#!/usr/bin/env python

"""
A class to perform calculation and approximations for obtaining quantities
    such as solar time, solar position, and the various types of solar irradiance.
"""
from simulation.common import constants, Race
from simulation.model.environment.solar_calculations.base_solar_calculations import BaseSolarCalculations
from simulation.model.environment import SolcastEnvironment


class SolcastSolarCalculations(BaseSolarCalculations):

    def __init__(self, race: Race):
        """

        Initializes the instance of a SolarCalculations class

        """

        # Solar Constant in W/m2
        self.S_0 = constants.SOLAR_IRRADIANCE
        self.race = race

    def calculate_array_GHI(self, coords, time_zones, local_times,
                            elevations, environment: SolcastEnvironment):
        """

        Calculates the Global Horizontal Irradiance from the Sun, relative to a location
        on the Earth, for arrays of coordinates, times, elevations and weathers
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation
        Note: If local_times and time_zones are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        :param np.ndarray coords: (float[N][lat, lng]) array of latitudes and longitudes
        :param np.ndarray time_zones: (int[N]) time zones at different locations in seconds relative to UTC
        :param np.ndarray local_times: (int[N]) unix time that the vehicle will be at each location. (Adjusted for Daylight Savings)
        :param np.ndarray elevations: (float[N]) elevation from sea level in m
        :param SolcastEnvironment environment: environment data object
        :returns: (float[N]) Global Horizontal Irradiance in W/m2
        :rtype: np.ndarray

        """
        return environment.ghi

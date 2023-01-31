#!/usr/bin/env python


"""
A class to perform calculation and approximations for obtaining quantities
    such as solar time, solar position, and the various types of solar irradiance.
"""

import datetime
import numpy as np
import sys
from simulation.common import helpers
from tqdm import tqdm


class SolarCalculations:

    def __init__(self):
        """
        Initializes the instance of a SolarCalculations class
        """

        # Solar Constant in W/m2
        self.S_0 = 1353

    # ----- Calculation of solar position in the sky -----

    @staticmethod
    def calculate_hour_angle(time_zone_utc, day_of_year, local_time, longitude):
        """
        Calculates and returns the Hour Angle of the Sun in the sky.
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight. (Adjust for Daylight Savings)
        longitude: The longitude of a location on Earth

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        Returns: The Hour Angle in degrees.
        """

        lst = helpers.local_time_to_apparent_solar_time(time_zone_utc / 3600, day_of_year,
                                                        local_time, longitude)

        hour_angle = 15 * (lst - 12)

        return hour_angle

    def calculate_elevation_angle(self, latitude, longitude, time_zone_utc, day_of_year,
                                  local_time):
        """
        Calculates the Elevation Angle of the Sun relative to a location on the Earth
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/elevation-angle

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset. For example,
            Vancouver has time_zone_utc = -7
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight. (Adjust for Daylight Savings)

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: The elevation angle in degrees
        """
        # Negative declination angles: Northern Hemisphere winter
        # 0 declination angle : Equinoxes (March 22, Sept 22)
        # Positive declination angle: Northern Hemisphere summer
        declination_angle = helpers.calculate_declination_angle(day_of_year)

        # Negative hour angles: Morning
        # 0 hour angle : Solar noon
        # Positive hour angle: Afternoon
        hour_angle = self.calculate_hour_angle(time_zone_utc, day_of_year,
                                               local_time, longitude)
        # From: https://en.wikipedia.org/wiki/Hour_angle#:~:text=At%20solar%20noon%20the%20hour,times%201.5%20hours%20before%20noon).
        # "For example, at 10:30 AM local apparent time
        # the hour angle is −22.5° (15° per hour times 1.5 hours before noon)."

        # mathy part is delegated to a helper function to optimize for numba compilation
        return helpers.compute_elevation_angle_math(declination_angle, hour_angle, latitude)

    def calculate_zenith_angle(self, latitude, longitude, time_zone_utc, day_of_year,
                               local_time):
        """
        Calculates the Zenith Angle of the Sun relative to a location on the Earth
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/azimuth-angle

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight. (Adjust for Daylight Savings)

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: The zenith angle in degrees
        """

        elevation_angle = self.calculate_elevation_angle(latitude, longitude,
                                                         time_zone_utc, day_of_year, local_time)

        return 90 - elevation_angle

    def calculate_azimuth_angle(self, latitude, longitude, time_zone_utc, day_of_year,
                                local_time):
        """
        Calculates the Azimuth Angle of the Sun relative to a location on the Earth.
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/azimuth-angle

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset. For example,
            Vancouver has time_zone_utc = -7
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight. (Adjust for Daylight Savings)

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: The azimuth angle in degrees
        """

        declination_angle = helpers.calculate_declination_angle(day_of_year)
        hour_angle = self.calculate_hour_angle(time_zone_utc, day_of_year,
                                               local_time, longitude)

        term_1 = np.sin(np.radians(declination_angle)) * \
            np.sin(np.radians(latitude))

        term_2 = np.cos(np.radians(declination_angle)) * \
            np.sin(np.radians(latitude)) * \
            np.cos(np.radians(hour_angle))

        elevation_angle = self.calculate_elevation_angle(latitude, longitude,
                                                         time_zone_utc, day_of_year, local_time)

        term_3 = np.float_(term_1 - term_2) / \
            np.cos(np.radians(elevation_angle))

        if term_3 < -1:
            term_3 = -1
        elif term_3 > 1:
            term_3 = 1

        azimuth_angle = np.arcsin(term_3)

        return np.degrees(azimuth_angle)

    # ----- Calculation of sunrise and sunset times -----

    # ----- Calculation of modes of solar irradiance -----

    def calculate_DNI(self, latitude, longitude, time_zone_utc, day_of_year,
                      local_time, elevation):
        """
        Calculates the Direct Normal Irradiance from the Sun, relative to a location
        on the Earth (clearsky)
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight. (Adjust for Daylight Savings)
        elevation: The local elevation of a location in metres

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: The Direct Normal Irradiance in W/m2
        """

        zenith_angle = self.calculate_zenith_angle(latitude, longitude,
                                                   time_zone_utc, day_of_year, local_time)
        a = 0.14

        # air_mass = 1 / (math.cos(math.radians(zenith_angle)) + \
        #            0.50572*pow((96.07995 - zenith_angle), -1.6364))

        air_mass = np.float_(1) / np.float_(np.cos(np.radians(zenith_angle)))
        with np.errstate(over="ignore"):
            DNI = self.S_0 * ((1 - a * elevation * 0.001) * np.power(np.power(0.7, air_mass),
                                                                     0.678) + a * elevation * 0.001)
        return np.where(zenith_angle > 90, 0, DNI)

    def calculate_DHI(self, latitude, longitude, time_zone_utc, day_of_year,
                      local_time, elevation):
        """
        Calculates the Diffuse Horizontal Irradiance from the Sun, relative to a location
        on the Earth (clearsky)
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth
        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight
        elevation: The local elevation of a location in metres

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        Returns: The Diffuse Horizontal Irradiance in W/m2
        """

        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        DHI = 0.1 * DNI

        return DHI

    def calculate_GHI(self, latitude, longitude, time_zone_utc, day_of_year,
                      local_time, elevation, cloud_cover):
        """
        Calculates the Global Horizontal Irradiance from the Sun, relative to a location
        on the Earth
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth
        time_zone_utc: The UTC time zone of your area in hours of UTC offset, without
            including the effects of Daylight Savings Time. For example, Vancouver
             has time_zone_utc = -8 year-round.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight.
        elevation: The local elevation of a location in metres
        cloud_cover: A NumPy array representing cloud cover as a percentage from 0 to 100

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        Returns: The Global Horizontal Irradiance in W/m^2
        """

        DHI = self.calculate_DHI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        zenith_angle = self.calculate_zenith_angle(latitude, longitude,
                                                   time_zone_utc, day_of_year, local_time)

        GHI = DNI * np.cos(np.radians(zenith_angle)) + DHI

        return self.apply_cloud_cover(GHI=GHI, cloud_cover=cloud_cover)

    @staticmethod
    def apply_cloud_cover(GHI, cloud_cover):
        """
        Applies a cloud cover model to the GHI data.

        Cloud cover adjustment follows the equation laid out here:
        http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/

        Args:
            GHI: Global Horizontal Index in W/m^2
            cloud_cover: A NumPy array representing cloud cover as a percentage from 0 to 100

        Returns: GHI after considering cloud cover data

        """

        assert np.logical_and(cloud_cover >= 0, cloud_cover <= 100).all()

        scaled_cloud_cover = cloud_cover / 100

        assert np.logical_and(scaled_cloud_cover >= 0,
                              scaled_cloud_cover <= 1).all()

        return GHI * (1 - (0.75 * np.power(scaled_cloud_cover, 3.4)))

    # ----- Calculation of modes of solar irradiance, but returning numpy arrays -----
    def calculate_array_GHI(self, coords, time_zones, local_times,
                            elevations, cloud_covers):
        """
        Calculates the Global Horizontal Irradiance from the Sun, relative to a location
        on the Earth, for arrays of coordinates, times, elevations and weathers
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation

        coords: (float[N][lat, lng]) array of latitudes and longitudes
        time_zones: (int[N]) time zones at different locations in seconds relative to UTC
        local_times: (int[N]) unix time that the vehicle will be at each location. 
                        (Adjusted for Daylight Savings)
        elevations: (float[N]) elevation from sea level in m
        cloud_covers: (float[N]) percentage cloud cover in range of 0 to 1 

        note: If local_times and time_zones are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: (float[N]) Global Horizontal Irradiance in W/m2
        """

        date = list(map(
            datetime.datetime.utcfromtimestamp, local_times))
        day_of_year = np.array(
            list(map(helpers.get_day_of_year_map, date)), dtype=np.float64)
        local_time = np.array(list(map(lambda date: date.hour +
                                       (float(date.minute * 60 + date.second) / 3600), date)))

        ghi = self.calculate_GHI(coords[:, 0], coords[:, 1], time_zones,
                                 day_of_year, local_time, elevations, cloud_covers)

        return ghi

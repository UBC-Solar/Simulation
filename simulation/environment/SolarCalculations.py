#!/usr/bin/env python


"""
A class to perform calculation and approximations for obtaining quantities
    such as solar time, solar position, and the various types of solar irradiance.
"""

import math
import datetime
import numpy as np
from simulation.common import helpers
from tqdm import tqdm
import sys


class SolarCalculations:

    def __init__(self):
        """
        Initializes the instance of a SolarCalculations class
        """

        # Solar Constant in W/m2
        self.S_0 = 1353

    # ----- Calculation of Apparent Solar Time -----

    @staticmethod
    def calculate_eot_correction(day_of_year):
        """
        Approximates and returns the correction factor between the apparent 
        solar time and the mean solar time

        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.

        Returns: The Equation of Time correction EoT in minutes, where
            Apparent Solar Time = Mean Solar Time + EoT
        """

        b = math.radians((float(360) / 364) * (day_of_year - 81))

        eot = 9.87 * math.sin(2 * b) - 7.83 * math.cos(b) - 1.5 * math.sin(b)

        return eot

    @staticmethod
    def calculate_LSTM(time_zone_utc):
        """
        Calculates and returns the LSTM, or Local Solar Time Meridian.
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

        time_zone_utc: The UTC time zone of your area in hours of UTC offset.

        Returns: The Local Solar Time Meridian in degrees
        """

        return 15 * time_zone_utc

    def local_time_to_apparent_solar_time(self, time_zone_utc, day_of_year, local_time,
                                          longitude):
        """
        Converts between the local time to the apparent solar time and returns the apparent
        solar time.
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

        time_zone_utc: The UTC time zone of your area in hours of UTC offset. 
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight (Adjust for Daylight Savings)
        longitude: The longitude of a location on Earth

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: The Apparent Solar Time of a location, in hours from midnight
        """

        lstm = self.calculate_LSTM(time_zone_utc)
        eot = self.calculate_eot_correction(day_of_year)

        # local solar time
        lst = local_time + float(longitude - lstm) / 15 + float(eot) / 60

        return lst

    # ----- Calculation of solar position in the sky -----

    def calculate_hour_angle(self, time_zone_utc, day_of_year, local_time, longitude):
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

        lst = self.local_time_to_apparent_solar_time(time_zone_utc, day_of_year,
                                                     local_time, longitude)

        hour_angle = 15 * (lst - 12)

        return hour_angle

    @staticmethod
    def calculate_declination_angle(day_of_year):
        """
        Calculates the Declination Angle of the Earth at a given day
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/declination-angle
        
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
       
        Returns: The declination angle of the Earth relative to the Sun, in 
            degrees
        """

        declination_angle = -23.45 * math.cos(math.radians((float(360) / 365) *
                                                           (day_of_year + 10)))

        return declination_angle

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

        declination_angle = self.calculate_declination_angle(day_of_year)
        hour_angle = self.calculate_hour_angle(time_zone_utc, day_of_year,
                                               local_time, longitude)

        term_1 = math.sin(math.radians(declination_angle)) * \
            math.sin(math.radians(latitude))

        term_2 = math.cos(math.radians(declination_angle)) * \
            math.cos(math.radians(latitude)) * \
            math.cos(math.radians(hour_angle))

        elevation_angle = math.asin(term_1 + term_2)

        return math.degrees(elevation_angle)

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

        declination_angle = self.calculate_declination_angle(day_of_year)
        hour_angle = self.calculate_hour_angle(time_zone_utc, day_of_year,
                                               local_time, longitude)

        term_1 = math.sin(math.radians(declination_angle)) * \
            math.sin(math.radians(latitude))

        term_2 = math.cos(math.radians(declination_angle)) * \
            math.sin(math.radians(latitude)) * \
            math.cos(math.radians(hour_angle))

        elevation_angle = self.calculate_elevation_angle(latitude, longitude,
                                                         time_zone_utc, day_of_year, local_time)

        term_3 = float(term_1 - term_2) / math.cos(math.radians(elevation_angle))

        if term_3 < -1:
            term_3 = -1
        elif term_3 > 1:
            term_3 = 1

        azimuth_angle = math.asin(term_3)

        return math.degrees(azimuth_angle)

    # ----- Calculation of sunrise and sunset times -----

    def calculate_sunrise_time(self, latitude, day_of_year):
        """
        Calculates the sunrise time relative to a location on the Earth
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation

        latitude: The latitude of a location on Earth
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.

        Returns: The sunrise time in hours from midnight. (Not adjusted for Daylight Savings)
        """

        declination_angle = self.calculate_declination_angle(day_of_year)

        term_1 = -math.sin(math.radians(latitude)) * \
            math.sin(math.radians(declination_angle))

        term_2 = math.cos(math.radians(latitude)) * \
            math.cos(math.radians(declination_angle))

        sunrise_time = 12 - (float(1) / 15) * math.degrees(math.acos(float(term_1) / term_2))

        return sunrise_time

    def calculate_sunset_time(self, latitude, day_of_year):
        """
        Calculates the sunset time relative to a location on the Earth
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation

        latitude: The latitude of a location on Earth
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.

        Returns: The sunset time in hours from midnight. (Not adjusted for Daylight Savings)
        """

        declination_angle = self.calculate_declination_angle(day_of_year)

        term_1 = -math.sin(math.radians(latitude)) * \
            math.sin(math.radians(declination_angle))

        term_2 = math.cos(math.radians(latitude)) * \
            math.cos(math.radians(declination_angle))

        sunset_time = 12 + (float(1) / 15) * math.degrees(math.acos(float(term_1) / term_2))

        return sunset_time

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

        if zenith_angle > 90:

            return 0

        else:

            # air_mass = 1 / (math.cos(math.radians(zenith_angle)) + \
            #            0.50572*pow((96.07995 - zenith_angle), -1.6364))

            air_mass = float(1) / float(math.cos(math.radians(zenith_angle)))

            DNI = self.S_0 * ((1 - a * elevation * 0.001) * math.pow(math.pow(0.7, air_mass),
                                                                     0.678) + a * elevation * 0.001)

            return DNI

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

        note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the 
                calculation will end up just the same

        Returns: The Global Horizontal Irradiance in W/m2 
        """

        DHI = self.calculate_DHI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        zenith_angle = self.calculate_zenith_angle(latitude, longitude,
                                                   time_zone_utc, day_of_year, local_time)

        cloud_cover_correction_factor = 1 - (cloud_cover / 100)

        GHI = DNI * math.cos(math.radians(zenith_angle)) + DHI
        GHI = cloud_cover_correction_factor * GHI

        return GHI

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

        ghi = np.zeros(len(coords))

        with tqdm(total=len(coords), file=sys.stdout, desc="Calculating GHI at each time step") as pbar:
            for i, _ in enumerate(coords):
                date = datetime.datetime.utcfromtimestamp(local_times[i])

                day_of_year = self.get_day_of_year(date.day, date.month, date.year)

                local_time = date.hour + (float(date.minute * 60 + date.second) / 3600)

                ghi[i] = self.calculate_GHI(coords[i][0], coords[i][1], time_zones[i],
                                            day_of_year, local_time, elevations[i], cloud_covers[i])

                pbar.update(1)
        print()

        return ghi

    # ----- Helper Functions -----

    @staticmethod
    def get_day_of_year(day, month, year):
        """
        Calculates the day of the year, given the day, month and year.

        day, month, year: self explanatory
        """

        return (datetime.date(year, month, day) -
                datetime.date(year, 1, 1)).days + 1

#!/usr/bin/env python

"""
A class to perform calculation and approximations for obtaining quantities
    such as solar time, solar position, and the various types of solar irradiance.
"""

import datetime
import numpy as np

from simulation.common import helpers, constants, ASC, FSGP


class SolarCalculations:

    def __init__(self, latitude, longitude, time_zone, unix_time, golang=True, library=None, race_type="ASC"):
        """

        Initializes the instance of a SolarCalculations class

        :param golang: Boolean that determines whether GoLang implementations will be used when applicable.
        :param library: GoLang binaries library

        """

        # Solar Constant in W/m2
        self.S_0 = constants.SOLAR_IRRADIANCE

        self.golang = golang
        self.lib = library
        self.race_type = race_type

        self.latitude = latitude
        self.longitude = longitude
        self.time_zone = time_zone
        self.excel_date = np.floor((unix_time / 86400) + 25569)  # convert to days, then add 70 years
        self.local_time_past_midnight = (unix_time / 86400) % 1

    # ----- Calculation of modes of solar irradiance -----

    def calculate_DNI(self, latitude, longitude, time_zone_utc, day_of_year,
                      local_time, elevation):
        """

        Calculates the Direct Normal Irradiance from the Sun, relative to a location
        on the Earth (clearsky)
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation
        Note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        :param np.ndarray latitude: The latitude of a location on Earth
        :param np.ndarray longitude: The longitude of a location on Earth
        :param np.ndarray time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        :param np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
        :param np.ndarray local_time: The local time in hours from midnight. (Adjust for Daylight Savings)
        :param np.ndarray elevation: The local elevation of a location in metres
        :returns: The Direct Normal Irradiance in W/m2
        :rtype: np.ndarray

        """

        zenith_angle = self.solar_zenith_angle()
        a = 0.14

        # https://www.pveducation.org/pvcdrom/properties-of-sunlight/air-mass
        # air_mass = 1 / (math.cos(math.radians(zenith_angle)) + \
        #            0.50572*pow((96.07995 - zenith_angle), -1.6364))

        with np.errstate(invalid="ignore"):
            air_mass = np.float_(1) / (np.float_(np.cos(np.radians(zenith_angle)))
                                       + 0.50572*np.power((96.07995 - zenith_angle), -1.6364))

        with np.errstate(over="ignore"):
            DNI = self.S_0 * ((1 - a * elevation * 0.001) * np.power(0.7, np.power(air_mass, 0.678))
                                  + a * elevation * 0.001)

        return np.where(zenith_angle > 90, 0, DNI)

    def calculate_DHI(self, latitude, longitude, time_zone_utc, day_of_year,
                      local_time, elevation):
        """

        Calculates the Diffuse Horizontal Irradiance from the Sun, relative to a location
        on the Earth (clearsky)
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation
        Note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        :param np.ndarray latitude: The latitude of a location on Earth
        :param np.ndarray longitude: The longitude of a location on Earth
        :param np.ndarray time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        :param np.ndarray np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
        :param np.ndarray local_time: The local time in hours from midnight
        :param np.ndarray elevation: The local elevation of a location in metres
        :returns: The Diffuse Horizontal Irradiance in W/m2
        :rtype: np.ndarray

        """

        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        DHI = 0.08 * DNI

        return DHI

    def calculate_GHI(self, latitude, longitude, time_zone_utc, day_of_year,
                      local_time, elevation, cloud_cover):
        """

        Calculates the Global Horizontal Irradiance from the Sun, relative to a location
        on the Earth
        https://www.pveducation.org/pvcdrom/properties-of-sunlight/calculation-of-solar-insolation
        Note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
                calculation will end up just the same

        :param np.ndarray latitude: The latitude of a location on Earth
        :param np.ndarray longitude: The longitude of a location on Earth
        :param np.ndarray time_zone_utc: The UTC time zone of your area in hours of UTC offset, without including the effects of Daylight Savings Time. For example, Vancouver has time_zone_utc = -8 year-round.
        :param np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
        :param np.ndarray local_time: The local time in hours from midnight.
        :param np.ndarray elevation: The local elevation of a location in metres
        :param np.ndarray cloud_cover: A NumPy array representing cloud cover as a percentage from 0 to 100
        :returns: The Global Horizontal Irradiance in W/m^2
        :rtype: np.ndarray

        """

        DHI = self.calculate_DHI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        zenith_angle = self.solar_zenith_angle()

        GHI = DNI * np.cos(np.radians(zenith_angle)) + DHI

        return self.apply_cloud_cover(GHI=GHI, cloud_cover=cloud_cover)

    @staticmethod
    def apply_cloud_cover(GHI, cloud_cover):
        """

        Applies a cloud cover model to the GHI data.

        Cloud cover adjustment follows the equation laid out here:
        http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/

        :param np.ndarray GHI: Global Horizontal Index in W/m^2
        :param np.ndarray cloud_cover: A NumPy array representing cloud cover as a percentage from 0 to 100

        :returns: GHI after considering cloud cover data
        :rtype: np.ndarray

        """

        assert np.logical_and(cloud_cover >= 0, cloud_cover <= 100).all()

        scaled_cloud_cover = cloud_cover / 100

        assert np.logical_and(scaled_cloud_cover >= 0,
                              scaled_cloud_cover <= 1).all()

        return GHI * (1 - (0.75 * np.power(scaled_cloud_cover, 3.4)))

    # ----- Calculation of modes of solar irradiance, but returning numpy arrays -----
    def python_calculate_array_GHI_times(self, local_times):
        date = list(map(datetime.datetime.utcfromtimestamp, local_times))
        day_of_year = np.array(list(map(helpers.get_day_of_year_map, date)), dtype=np.float64)
        local_time = np.array(list(map(SolarCalculations.dateConvert, date)))
        return day_of_year, local_time

    @staticmethod
    def dateConvert(date):
        """

        Convert a date into local time.

        :param datetime.datetime date: date to be converted
        :return: a date converted into local time.
        :rtype: int

        """

        return date.hour + (float(date.minute * 60 + date.second) / 3600)

    def calculate_array_GHI(self, coords, time_zones, local_times,
                            elevations, cloud_covers):
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
        :param np.ndarray cloud_covers: (float[N]) percentage cloud cover in range of 0 to 1
        :returns: (float[N]) Global Horizontal Irradiance in W/m2
        :rtype: np.ndarray

        """

        if not self.golang:
            day_of_year, local_time = self.python_calculate_array_GHI_times(local_times)
        else:
            day_of_year, local_time = self.lib.golang_calculate_array_GHI_times(local_times)

        ghi = self.calculate_GHI(coords[:, 0], coords[:, 1], time_zones,
                                 day_of_year, local_time, elevations, cloud_covers)

        stationary_irradiance = self.calculate_angled_irradiance(coords[:, 0], coords[:, 1], time_zones, day_of_year,
                                                                 local_time, elevations, cloud_covers)

        if self.race_type == "ASC":
            driving_begin = ASC.driving_begin
            driving_end = ASC.driving_end
        elif self.race_type == "FSGP":
            driving_begin = FSGP.driving_begin
            driving_end = FSGP.driving_end
        else:
            driving_begin = 0
            driving_end = 24

        # Use stationary irradiance when the car is not driving
        effective_irradiance = np.where(
            np.logical_or(
                (local_time < driving_begin),
                (driving_end < local_time)),
            stationary_irradiance,
            ghi)

        return effective_irradiance

    def calculate_angled_irradiance(self, latitude, longitude, time_zone_utc, day_of_year,
                                    local_time, elevation, cloud_cover, array_angles=np.array([0, 15, 30, 45])):
        """

        Determine the direct and diffuse irradiance on an array which can be mounted at different angles.
        During stationary charging, the car can mount the array at different angles, resulting in a higher
        component of direct irradiance captured.

        Uses the GHI formula, GHI = DNI*cos(zenith)+DHI but with an 'effective zenith',
        the angle between the mounted panel's normal and the sun.

        :param np.ndarray latitude: The latitude of a location on Earth
        :param np.ndarray longitude: The longitude of a location on Earth
        :param np.ndarray time_zone_utc: The UTC time zone of your area in hours of UTC offset, without including the effects of Daylight Savings Time. For example, Vancouver has time_zone_utc = -8 year-round.
        :param np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
        :param np.ndarray local_time: The local time in hours from midnight.
        :param np.ndarray elevation: The local elevation of a location in metres
        :param np.ndarray cloud_cover: A NumPy array representing cloud cover as a percentage from 0 to 100
        :param np.ndarray array_angles: An array containing the discrete angles on which the array can be mounted
        :returns: The "effective Global Horizontal Irradiance" in W/m^2
        :rtype: np.ndarray

        """

        DHI = self.calculate_DHI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year,
                                 local_time, elevation)

        zenith_angle = self.solar_zenith_angle()

        # Calculate the absolute differences
        differences = np.abs(zenith_angle[:, np.newaxis] - array_angles)

        # Find the minimum difference for each element in zenith_angle
        effective_zenith = np.min(differences, axis=1)

        # Now effective_zenith contains the minimum absolute difference for each element in zenith_angle

        GHI = DNI * np.cos(np.radians(effective_zenith)) + DHI

        return self.apply_cloud_cover(GHI=GHI, cloud_cover=cloud_cover)

    # ----- Set parameters for solar position calculations -----
    def set_time_and_date(self, latitude, longitude, time_zone, unix_time):
        self.latitude = latitude
        self.longitude = longitude
        self.time_zone = time_zone
        self.excel_date = np.floor((unix_time / 86400) + 25569)  # convert to days, then add 70 years
        self.local_time_past_midnight = (unix_time / 86400) % 1

    # ----- Calculation of solar position in the sky using NOAA formulae -----

    def julian_day(self):
        return self.excel_date + 2415018.5 + self.local_time_past_midnight - self.time_zone / 24

    def julian_century(self):
        return (self.julian_day() - 2451545) / 36525

    def geom_mean_long_sum(self):
        return (280.46646 + self.julian_century() * (36000.76983 + self.julian_century() * 0.0003032)) % 360

    def geom_mean_anom_sum(self):
        return 357.52911 + self.julian_century() * (35999.05029 - 0.0001537 * self.julian_century())

    def eccent_earth_orbit(self):
        return 0.016708634 - self.julian_century() * (0.000042037 + 0.0000001267 * self.julian_century())

    def sun_eq_of_ctr(self):
        return (
            np.sin(np.radians(self.geom_mean_anom_sum())) *
            (1.914602 - self.julian_century() * (0.004817 + 0.000014 * self.julian_century())) +
            np.sin(np.radians(2 * self.geom_mean_anom_sum())) * (0.019993 - 0.000101 * self.julian_century()) +
            np.sin(np.radians(3 * self.geom_mean_anom_sum())) * 0.000289
        )

    def sun_true_long(self):
        return self.geom_mean_long_sum() + self.sun_eq_of_ctr()

    def sun_true_anom(self):
        return self.geom_mean_anom_sum() + self.sun_eq_of_ctr()

    def sun_rad_vector(self):
        return ((1.000001018 * (1 - self.eccent_earth_orbit() * self.eccent_earth_orbit())) /
                (1 + self.eccent_earth_orbit() * np.cos(np.radians(self.sun_true_anom()))))

    def sun_app_long(self):
        return self.sun_true_long() - 0.00569 - 0.00478 * np.sin(np.radians(125.04 - 1934.136 * self.julian_century()))

    def mean_obliq_ecliptic(self):
        return 23 + (
            26 + (
                21.448 - self.julian_century() * (
                    46.815 + self.julian_century() * (
                        0.00059 - self.julian_century() * 0.001813
                    )
                )
            ) / 60
        ) / 60

    def obliq_corr(self):
        return self.mean_obliq_ecliptic() + 0.00256 * np.cos(np.radians(125.04 - 1934.136 * self.julian_century()))

    def sun_rt_ascen(self):
        return np.degrees(np.arctan((np.cos(np.radians(self.obliq_corr())) * np.sin(np.radians(self.sun_app_long()))) /
                          np.cos(np.radians(self.sun_app_long()))))

    def sun_declin(self):
        return np.degrees(np.arcsin(np.sin(np.radians(self.obliq_corr())) * np.sin(np.radians(self.sun_app_long()))))

    def var_y(self):
        return np.tan(np.radians(self.obliq_corr() / 2)) * np.tan(np.radians(self.obliq_corr() / 2))

    def eq_of_time(self):
        return 4 * np.degrees(
            self.var_y() * np.sin(2 * np.radians(self.geom_mean_long_sum())) -
            2 * self.eccent_earth_orbit() * np.sin(np.radians(self.geom_mean_anom_sum())) +
            4 * self.eccent_earth_orbit() * self.var_y() * np.sin(np.radians(self.geom_mean_anom_sum())) * np.cos(
                2 * np.radians(self.geom_mean_long_sum())) -
            0.5 * self.var_y() ** 2 * np.sin(4 * np.radians(self.geom_mean_long_sum())) -
            1.25 * self.eccent_earth_orbit() ** 2 * np.sin(2 * np.radians(self.geom_mean_anom_sum()))
        )

    def ha_sunrise(self):
        return np.degrees(np.arccos(
            np.cos(np.radians(90.833)) / (np.cos(np.radians(self.latitude)) * np.cos(np.radians(self.sun_declin()))) -
            np.tan(np.radians(self.latitude)) * np.tan(np.radians(self.sun_declin()))
        ))

    def solar_noon(self):
        return (720 - 4 * self.longitude - self.eq_of_time() + self.time_zone * 60) / 1440

    def sunrise_time(self):
        return self.solar_noon() - self.ha_sunrise() * 4 / 1440

    def sunset_time(self):
        return self.solar_noon() + self.ha_sunrise() * 4 / 1440

    def sunlight_duration(self):
        return 8 * self.ha_sunrise()

    def true_solar_time(self):
        return (self.local_time_past_midnight * 1440 + self.eq_of_time() + 4 * self.longitude - 60 * self.time_zone) % 1440

    def hour_angle(self):
        true_solar_time = self.true_solar_time()

        return np.where(
            true_solar_time / 4 < 0,
            true_solar_time / 4 + 180,
            true_solar_time / 4 - 180
        )

    def solar_zenith_angle(self):
        return np.degrees(np.arccos(
            np.sin(np.radians(self.latitude)) * np.sin(np.radians(self.sun_declin())) +
            np.cos(np.radians(self.latitude)) * np.cos(np.radians(self.sun_declin())) *
            np.cos(np.radians(self.hour_angle()))
        ))

    def solar_elevation_angle(self):
        return 90 - self.solar_zenith_angle()

    def approx_atmospheric_refraction(self):
        solar_elevation_angle = self.solar_elevation_angle()

        return np.where(
            solar_elevation_angle > 85,
            0,
            np.where(
                solar_elevation_angle > 5,
                58.1 / np.tan(np.radians(solar_elevation_angle)) - 0.07 / np.power(
                    np.tan(np.radians(solar_elevation_angle)), 3) + 0.000086 / np.power(
                    np.tan(np.radians(solar_elevation_angle)), 5),
                np.where(
                    solar_elevation_angle > -0.575,
                    1735 + solar_elevation_angle * (
                            -518.2 + solar_elevation_angle * (
                                    103.4 + solar_elevation_angle * (
                                            -12.79 + solar_elevation_angle * 0.711))),
                    -20.772 / np.tan(np.radians(solar_elevation_angle))
                )
            )
        ) / 3600

    def solar_elevation_corrected_for_atm_refraction(self):
        return self.solar_elevation_angle() + self.approx_atmospheric_refraction()

    def solar_azimuth_angle(self):
        solar_zenith_angle_rad = np.radians(self.solar_zenith_angle())
        latitude_rad = np.radians(self.latitude)
        sun_declin_rad = np.radians(self.sun_declin())
        hour_angle_rad = np.radians(self.hour_angle())

        cos_solar_zenith = np.cos(solar_zenith_angle_rad)

        return np.degrees(np.arccos(
            ((np.sin(latitude_rad) * np.cos(solar_zenith_angle_rad)) - np.sin(sun_declin_rad)) /
            (cos_solar_zenith * np.sin(solar_zenith_angle_rad))
        )) + 180 * (hour_angle_rad > 0) - 180 * (hour_angle_rad <= 0)

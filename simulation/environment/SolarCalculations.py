#!/usr/bin/env python


"""
A class to perform calculation and approximations for obtaining quantities
    such as solar time, solar position, and the various types of solar irradiance.
"""


import math


class SolarCalculations:


    def __init__(self):
        """
        Initializes the instance of a SolarCalculations class
        """

        #Solar Constant in W/m2
        self.S_0 = 1353


    def calculate_eot_correction(self, day_of_year):
        """
        Approximates and returns the correction factor between the apparent 
            solar time and the mean solar time

        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.

        Returns: The Equation of Time correction EoT in minutes, where
            Apparent Solar Time = Mean Solar Time + EoT
        """

        b = math.radians((float(360) / 364) * (day_of_year - 81))

        eot = 9.87*math.sin(2*b) - 7.83*math.cos(b) - 1.5*math.sin(b)

        return eot


    def calculate_LSTM(self, time_zone_utc):
        """
        Calculates and returns the LSTM, or Local Solar Time Meridian.

        time_zone_utc: The UTC time zone of your area in hours of UTC offset.

        Returns: The Local Solar Time Meridian in degrees
        """

        return 15*time_zone_utc


    def local_time_to_apparent_solar_time(self, time_zone_utc, day_of_year, local_time, \
            longitude):
        """
        Converts between the local time to the apparent solar time and returns the apparent
            solar time

        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        Confirm your email:local_time: The local time in hours from midnight
        longitude: The longitude of a location on Earth

        Returns: The Apparent Solar Time of a location, in hours from midnight
        """

        lstm = self.calculate_LSTM(time_zone_utc)
        eot = self.calculate_eot_correction(day_of_year)
        
        lst = local_time + float(longitude - lstm)/15 + float(eot)/60

        return lst

    
    def calculate_hour_angle(self, time_zone_utc, day_of_year, local_time, longitude):
        """
        Calculates and returns the Hour Angle of the Sun in the sky.
        
        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight
        longitude: The longitude of a location on Earth

        Returns: The Hour Angle in degrees. 
        """
    
        lst = self.local_time_to_apparent_solar_time(time_zone_utc, day_of_year, \
                    local_time, longitude)

        hour_angle = 15 * (lst - 12)

        return hour_angle


    def calculate_declination_angle(self, day_of_year):
        """
        Calculates the Declination Angle of the Earth at a given day
        
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
       
        Returns: The declination angle of the Earth relative to the Sun, in 
            degrees
        """

        declination_angle = -23.45 * math.cos(math.radians((float(360)/365) * \
             (day_of_year + 10)))

        return declination_angle


    def calculate_elevation_angle(self, latitude, longitude, time_zone_utc, day_of_year,\
            local_time):
        """
        Calculates the Elevation Angle of the Sun relative to a location on the Earth

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset. For example,
            Vancouver has time_zone_utc = -7
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight

        Returns: The elevation angle in degrees
        """
        
        declination_angle = self.calculate_declination_angle(day_of_year)
        hour_angle = self.calculate_hour_angle(time_zone_utc, day_of_year, \
            local_time, longitude)

        term_1 = math.sin(math.radians(declination_angle)) * \
                 math.sin(math.radians(latitude))

        term_2 = math.cos(math.radians(declination_angle)) * \
                 math.cos(math.radians(latitude)) * \
                 math.cos(math.radians(hour_angle))

        elevation_angle = math.asin(term_1 + term_2)

        return math.degrees(elevation_angle)


    def calculate_zenith_angle(self, latitude, longitude, time_zone_utc, day_of_year,\
            local_time):
        """
        Calculates the Zenith Angle of the Sun relative to a location on the Earth

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset. For example,
            Vancouver has time_zone_utc = -7
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight

        Returns: The zenith angle in degrees
        """

        elevation_angle = self.calculate_elevation_angle(latitude, longitude, \
                            time_zone_utc, day_of_year, local_time)

        return 90 - elevation_angle
        
    
    def calculate_azimuth_angle(self, latitude, longitude, time_zone_utc, day_of_year, \
            local_time):
        """
        Calculates the Azimuth Angle of the Sun relative to a location on the Earth

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset. For example,
            Vancouver has time_zone_utc = -7
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight

        Returns: The azimuth angle in degrees
        """

        declination_angle = self.calculate_declination_angle(day_of_year)
        hour_angle = self.calculate_hour_angle(time_zone_utc, day_of_year, \
            local_time, longitude)

        term_1 = math.sin(math.radians(declination_angle)) * \
                 math.sin(math.radians(latitude))

        term_2 = math.cos(math.radians(declination_angle)) * \
                 math.sin(math.radians(latitude)) * \
                 math.cos(math.radians(hour_angle)) 

        elevation_angle = self.calculate_elevation_angle(latitude, longitude,\
                             time_zone_utc, day_of_year, local_time)

        term_3 = float(term_1 - term_2) / math.cos(math.radians(elevation_angle))

        if term_3 < -1:
            term_3 = -1
        elif term_3 > 1:
            term_3 = 1

        azimuth_angle = math.asin(term_3)

        return math.degrees(azimuth_angle)


    def calculate_sunrise_time(self, latitude, day_of_year):
        """
        Calculates the sunrise time relative to a location on the Earth

        latitude: The latitude of a location on Earth
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.

        Returns: The sunrise time in hours from midnight 
        """

        declination_angle = self.calculate_declination_angle(day_of_year)

        term_1 = -math.sin(math.radians(latitude)) * \
                    math.sin(math.radians(declination_angle))

        term_2 = math.cos(math.radians(latitude)) * \
                    math.cos(math.radians(declination_angle)) 

        sunrise_time = 12 - (float(1)/15) * math.degrees(math.acos( float(term_1) / term_2))

        return sunrise_time


    def calculate_sunset_time(self, latitude, day_of_year):
        """
        Calculates the sunset time relative to a location on the Earth

        latitude: The latitude of a location on Earth
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.

        Returns: The sunset time in hours from midnight 
        """

        declination_angle = self.calculate_declination_angle(day_of_year)

        term_1 = -math.sin(math.radians(latitude)) * \
                    math.sin(math.radians(declination_angle))

        term_2 = math.cos(math.radians(latitude)) * \
                    math.cos(math.radians(declination_angle)) 

        sunset_time = 12 + (float(1)/15) * math.degrees(math.acos( float(term_1) / term_2))

        return sunset_time


    def calculate_DNI(self, latitude, longitude, time_zone_utc, day_of_year, \
            local_time, elevation):
        """
        Calculates the Direct Normal Irradiance from the Sun, relative to a location
            on the Earth (clearsky)

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight
        elevation: The local elevation of a location in metres

        Returns: The Direct Normal Irradiance in W/m2
        """

        zenith_angle = self.calculate_zenith_angle(latitude, longitude, \
                            time_zone_utc, day_of_year, local_time)
        a = 0.14

        if zenith_angle > 90:

            return 0

        else:

            #air_mass = 1 / (math.cos(math.radians(zenith_angle)) + \
            #            0.50572*pow((96.07995 - zenith_angle), -1.6364))

            air_mass = float(1) / float(math.cos(math.radians(zenith_angle)))

            DNI = self.S_0 * ((1 - a * elevation * 0.001) * math.pow(math.pow(0.7, air_mass), \
                    0.678) + a * elevation * 0.001)

            return DNI


    def calculate_DHI(self, latitude, longitude, time_zone_utc, day_of_year, \
            local_time, elevation):
        """
        Calculates the Diffuse Horizontal Irradiance from the Sun, relative to a location 
            on the Earth (clearsky)

        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight
        elevation: The local elevation of a location in metres

        Returns: The Diffuse Horizontal Irradiance in W/m2
        """
        
        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year, \
                local_time, elevation)
        
        DHI = 0.1 * DNI 
        
        return DHI
        
        
    def calculate_GHI(self, latitude, longitude, time_zone_utc, day_of_year, \
            local_time, elevation, cloud_cover):
        """
        Calculates the Global Horizontal Irradiance from the Sun, relative to a location
            on the Earth
        
        latitude: The latitude of a location on Earth
        longitude: The longitude of a location on Earth       
        time_zone_utc: The UTC time zone of your area in hours of UTC offset, without 
            including the effects of Daylight Savings Time. For example, Vancouver
             has time_zone_utc = -8 year-round.
        day_of_year: The number of the day of the current year, with January 1
            being the first day of the year.
        local_time: The local time in hours from midnight. 
        elevation: The local elevation of a location in metres

        Returns: The Global Horizontal Irradiance in W/m2 
        """
        
        DHI = self.calculate_DHI(latitude, longitude, time_zone_utc, day_of_year, \
            local_time, elevation)
        
        DNI = self.calculate_DNI(latitude, longitude, time_zone_utc, day_of_year, \
            local_time, elevation)
        
        zenith_angle = self.calculate_zenith_angle(latitude, longitude, \
                            time_zone_utc, day_of_year, local_time)
        
        GHI = DNI * math.cos(math.radians(zenith_angle)) + DHI
         
        return GHI



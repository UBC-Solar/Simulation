import numpy as np


class NoaaCalc:
    def __init__(self, latitude, longitude, time_zone, unix_time):

        """
        :param np.ndarray latitude: Array of latitudes
        :param np.ndarray longitude: Array of longitudes
        :param np.ndarray time_zone: Array of UTC time zone offsets in hours, e.g. -5
        :param np.ndarray unix_time: Unix timestamps used to find date and time
        """

        self.latitude = latitude
        self.longitude = longitude
        self.time_zone = time_zone
        self.excel_date = np.floor((unix_time / 86400) + 25569)  # convert to days, then add 70 years
        self.local_time_past_midnight = (unix_time / 86400) % 1

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

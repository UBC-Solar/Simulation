from math import cos, sin, tan, radians, degrees, acos, asin, atan, floor


def get_excel_date(gmt_unix_time):
    # Excel date format is in days since 1900
    return floor((gmt_unix_time / 86400) + 25569)  # convert to days, then add 70 years


class NoaaCalc:
    def __init__(self, latitude, longitude, time_zone, unix_time, local_time_past_midnight):
        self.latitude = latitude
        self.longitude = longitude
        self.time_zone = time_zone
        self.excel_date = get_excel_date(unix_time)
        self.local_time_past_midnight = local_time_past_midnight

    def julian_day(self):
        return self.excel_date+2415018.5+self.local_time_past_midnight-self.time_zone/24

    def julian_century(self):
        return (self.julian_day()-2451545)/36525

    def geom_mean_long_sum(self):
        return (280.46646+self.julian_century()*(36000.76983 + self.julian_century()*0.0003032)) % 360

    def geom_mean_anom_sum(self):
        return 357.52911+self.julian_century()*(35999.05029 - 0.0001537*self.julian_century())

    def eccent_earth_orbit(self):
        return 0.016708634-self.julian_century()*(0.000042037+0.0000001267*self.julian_century())

    def sun_eq_of_ctr(self):

        """
        =SIN(RADIANS(J2))*(1.914602-G2*(0.004817+0.000014*G2))
        +SIN(RADIANS(2*J2))*(0.019993-0.000101*G2)
        +SIN(RADIANS(3*J2))*0.000289
        """

        return (
            sin(radians(self.geom_mean_anom_sum())) * (1.914602 - self.julian_century() * (0.004817 + 0.000014 * self.julian_century())) +
            sin(radians(2 * self.geom_mean_anom_sum())) * (0.019993 - 0.000101 * self.julian_century()) +
            sin(radians(3 * self.geom_mean_anom_sum())) * 0.000289
        )

    def sun_true_long(self):
        return self.geom_mean_long_sum() + self.sun_eq_of_ctr()

    def sun_true_anom(self):
        return self.geom_mean_anom_sum() + self.sun_eq_of_ctr()

    def sun_rad_vector(self):
        return ((1.000001018 * (1 - self.eccent_earth_orbit() * self.eccent_earth_orbit()))
                / (1 + self.eccent_earth_orbit() * cos(radians(self.sun_true_anom()))))

    def sun_app_long(self):
        return self.sun_true_long()-0.00569-0.00478*sin(radians(125.04-1934.136*self.julian_century()))

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
        return self.mean_obliq_ecliptic() + 0.00256 * cos(radians(125.04 - 1934.136 * self.julian_century()))

    def sun_rt_ascen(self):
        return degrees(atan((cos(radians(self.obliq_corr())) * sin(radians(self.sun_app_long()))) / cos(radians(self.sun_app_long()))))

    def sun_declin(self):
        return degrees(asin(sin(radians(self.obliq_corr()))*sin(radians(self.sun_app_long()))))

    def var_y(self):
        return tan(radians(self.obliq_corr()/2))*tan(radians(self.obliq_corr()/2))

    def eq_of_time(self):

        """
        4*DEGREES(
            U2*SIN(2*RADIANS(I2))-
            2*K2*SIN(RADIANS(J2))+
            4*K2*U2*SIN(RADIANS(J2))*COS(
                2*RADIANS(I2))-
            0.5*U2*U2*SIN(4*RADIANS(I2))-
            1.25*K2*K2*SIN(2*RADIANS(J2))
        )
        """

        return 4 * degrees(
            self.var_y() * sin(2 * radians(self.geom_mean_long_sum())) -
            2 * self.eccent_earth_orbit() * sin(radians(self.geom_mean_anom_sum())) +
            4 * self.eccent_earth_orbit() * self.var_y() * sin(radians(self.geom_mean_anom_sum())) * cos(
                2 * radians(self.geom_mean_long_sum())) -
            0.5 * self.var_y() ** 2 * sin(4 * radians(self.geom_mean_long_sum())) -
            1.25 * self.eccent_earth_orbit() ** 2 * sin(2 * radians(self.geom_mean_anom_sum()))
        )

    def ha_sunrise(self):
        return degrees(acos(
            cos(radians(90.833)) / (cos(radians(self.latitude)) * cos(radians(self.sun_declin()))) -
            tan(radians(self.latitude)) * tan(radians(self.sun_declin()))
        ))

    def solar_noon(self):
        return (720-4*self.longitude-self.eq_of_time()+self.time_zone*60)/1440

    def sunrise_time(self):
        return self.solar_noon()-self.ha_sunrise()*4/1440

    def sunset_time(self):
        return self.solar_noon()+self.ha_sunrise()*4/1440

    def sunlight_duration(self):
        return 8*self.ha_sunrise()

    def true_solar_time(self):
        return (self.local_time_past_midnight*1440+self.eq_of_time()+4*self.longitude-60*self.time_zone) % 1440

    def hour_angle(self):
        return (self.true_solar_time()/4+180) if (self.true_solar_time()/4 < 0) else (self.true_solar_time()/4-180)

    def solar_zenith_angle(self):
        return degrees(acos(
            sin(radians(self.latitude))*sin(radians(self.sun_declin())) +
            cos(radians(self.latitude))*cos(radians(self.sun_declin()))*cos(radians(self.hour_angle()))
        ))

    def solar_elevation_angle(self):
        return 90 - self.solar_zenith_angle()

    def approx_atmospheric_refraction(self):

        """
        IF(
            AE2>85,
            0,

            IF(
                AE2>5,
                58.1/TAN(RADIANS(AE2))-0.07/POWER(TAN(RADIANS(AE2)),3)+0.000086/POWER(TAN(RADIANS(AE2)),5),

                IF(
                    AE2>-0.575,
                    1735+AE2*(-518.2+AE2*(103.4+AE2*(-12.79+AE2*0.711))),

                    -20.772/TAN(RADIANS(AE2))
                )
            )
        )/3600
        """

        return (
            0 if self.solar_elevation_angle() > 85 else
            (
                58.1 / tan(radians(self.solar_elevation_angle())) - 0.07 / pow(
                    tan(radians(self.solar_elevation_angle())), 3) + 0.000086 / pow(
                    tan(radians(self.solar_elevation_angle())), 5)
                if self.solar_elevation_angle() > 5
                else
                (
                    1735 + self.solar_elevation_angle() * (-518.2 + self.solar_elevation_angle() * (
                                103.4 + self.solar_elevation_angle() * (-12.79 + self.solar_elevation_angle() * 0.711)))
                    if self.solar_elevation_angle() > -0.575
                    else
                    -20.772 / tan(radians(self.solar_elevation_angle()))
                )
            )
        ) / 3600

    def solar_elevation_corrected_for_atm_refraction(self):
        return self.solar_elevation_angle()+self.approx_atmospheric_refraction()

    def solar_azimuth_angle(self):

        """
        IF(
        AC2>0,
        MOD(DEGREES(ACOS(((SIN(RADIANS($B$3))*COS(RADIANS(AD2)))-SIN(RADIANS(T2)))/(COS(RADIANS($B$3))*SIN(RADIANS(AD2)))))+180,360),

        MOD(540-DEGREES(ACOS(((SIN(RADIANS($B$3))*COS(RADIANS(AD2)))-SIN(RADIANS(T2)))/(COS(RADIANS($B$3))*SIN(RADIANS(AD2))))),360)
        )

        """

        return (
            degrees(acos(((sin(radians(self.latitude)) * cos(radians(self.solar_zenith_angle()))) - sin(
                radians(self.sun_declin()))) / (
                                     cos(radians(self.latitude)) * sin(radians(self.solar_zenith_angle()))))) + 180
            if self.hour_angle() > 0
            else (540 - degrees(acos(((sin(radians(self.latitude)) * cos(radians(self.solar_zenith_angle()))) - sin(
                radians(self.sun_declin()))) / (cos(radians(self.latitude)) * sin(
                radians(self.solar_zenith_angle())))))) % 360
        )


def testSunriseSunset():
    eg_latitude = 39.0918
    eg_longitude = -94.4172
    eg_time_zone = -6
    eg_unix_time = 1612080000  # 7am PST, Jan 31 2021
    eg_local_time_past_midnight = 0.31

    testDate = NoaaCalc(eg_latitude, eg_longitude, eg_time_zone, eg_unix_time, eg_local_time_past_midnight)

    sunrise_hours = testDate.sunrise_time() * 24
    sunset_hours = testDate.sunset_time() * 24
    sunrise_minutes = (sunrise_hours % 1) * 60
    sunset_minutes = (sunset_hours % 1) * 60
    sunrise_seconds = (sunrise_minutes % 1) * 60
    sunset_seconds = (sunset_minutes % 1) * 60

    print(f"Sunrise: {floor(sunrise_hours)}:{floor(sunrise_minutes)}:{floor(sunrise_seconds)}")
    print(f"Sunset: {floor(sunset_hours)}:{floor(sunset_minutes)}:{floor(sunset_seconds)}")


def print_all():
    eg_latitude = 39.0918
    eg_longitude = -94.4172
    eg_time_zone = -6
    eg_unix_time = 1612080000  # 7am PST, Jan 31 2021
    eg_local_time_past_midnight = 0.31

    test_date = NoaaCalc(eg_latitude, eg_longitude, eg_time_zone, eg_unix_time, eg_local_time_past_midnight)

    for method_name in dir(NoaaCalc):
        if callable(getattr(NoaaCalc, method_name)) and not method_name.startswith("__"):
            method = getattr(NoaaCalc, method_name)
            result = method(test_date)
            print(f"{method_name}: {result}")


if __name__ == "__main__":
    print_all()

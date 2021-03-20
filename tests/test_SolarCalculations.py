import numpy as np
import simulation


# Inputs for test:
# The following values for the input paremeters of
# the methods under testing will be used:
#
# latitude: 40
# longitude: -95
# time_zone_utc: -5
# local_time: 13
# day_of_year: will have varying values to create multiple test cases
# solar_constant: 1353
# elevation: 300
# cloud_cover: 4.5

# @pytest.fixture
# def solar_calc_test():
#     test_solar_calculations = simulation.SolarCalculations()
#
#     return


def test_calculate_declination_angle():
    test_solar_calculations = simulation.SolarCalculations()

    test_days_of_year = np.array([2, 4, 6, 20, 40, 60, 120, 140, 160, 180, 240, 260, 280, 318, 358])
    test_calculated_declination_angles = test_solar_calculations.calculate_declination_angle(test_days_of_year)
    test_expected_angles = ([-22.95145488, -22.77229622, -22.56614787, -20.39187118, -15.28703145,
                             -8.388023701, 14.50784441, 19.87483464, 22.90920766, 23.25483315, 9.322378995,
                             1.51272314, -6.474474019, -16.7590909, -23.41873684])

    assert np.all(True == np.allclose(test_calculated_declination_angles, test_expected_angles, rtol=1e-05, atol=1e-06))


def test_calculate_elevation_angle():
    test_solar_calculations = simulation.SolarCalculations()

    test_latitude = 40
    test_longitude = -95
    test_time_zone_utc = -5
    test_local_time = 13

    test_days_of_year = np.array([2, 4, 6, 20, 40, 60, 120, 140, 160, 180, 240, 260, 280, 318, 358])
    expected_elevation_angles = np.array([26.79712078, 26.95700167, 27.14348312, 29.17781758, 34.13241352, 41.01217067,
                                          64.23086965, 69.56996524, 72.44277623, 72.55926997, 58.97443129, 51.38586111,
                                          43.49714762, 33.23395048, 26.40958008])
    # populate the two above arrays with hour and declination angles corresponding to the day of year
    test_elevation_angles = np.array([])
    for day in test_days_of_year:
        np.append(test_elevation_angles,
                  test_solar_calculations.calculate_elevation_angle(test_latitude, test_longitude,
                                                                    test_time_zone_utc, day,
                                                                    test_local_time))

    assert np.all(True == np.allclose(test_elevation_angles, expected_elevation_angles, rtol=1e-05, atol=1e-06))


def test_calculate_zenith_angle():
    test_solar_calculations = simulation.SolarCalculations()

    test_latitude = 40
    test_longitude = -95
    test_time_zone_utc = -5
    test_local_time = 13

    test_days_of_year = np.array([2, 4, 6, 20, 40, 60, 120, 140, 160, 180, 240, 260, 280, 318, 358])
    test_elevation_angles = np.array([26.79712078, 26.95700167, 27.14348312, 29.17781758, 34.13241352, 41.01217067,
                                      64.23086965, 69.56996524, 72.44277623, 72.55926997, 58.97443129, 51.38586111,
                                      43.49714762, 33.23395048, 26.40958008])

    expected_zenith_angles = 90 - test_elevation_angles
    test_zenith_angles = np.array([])
    for day in test_days_of_year:
        np.append(test_zenith_angles, test_solar_calculations.calculate_zenith_angle(test_latitude, test_longitude,
                                                                                     test_time_zone_utc, day,
                                                                                     test_local_time))
    assert (True == np.allclose(test_zenith_angles, expected_zenith_angles, rtol=1e-05, atol=1e-06))


def test_calculate_azimuth_angle():
    test_solar_calculations = simulation.SolarCalculations()

    test_latitude = 40
    test_longitude = -95
    test_time_zone_utc = -5
    test_local_time = 13

    test_days_of_year = np.array([2, 4, 6, 20, 40, 60, 120, 140, 160, 180, 240, 260, 280, 318, 358])

    expected_azimuth_angles = ([-90, -90, -90, -86.38491457, -68.91855021, -58.52604317, -36.69494539,
                                -32.12153706, -29.45678099, -29.07362992, -41.09961618, -48.39060894,
                                -56.99565412, -73.63915528, -90])

    test_azimuth_angles = np.array([])
    for day in test_days_of_year:
        np.append(test_azimuth_angles, test_solar_calculations.calculate_azimuth_angle(test_latitude, test_longitude,
                                                                                       test_time_zone_utc, day,
                                                                                       test_local_time))
    assert (True == np.allclose(test_azimuth_angles, expected_azimuth_angles, rtol=1e-05, atol=1e-06))


def test_calculate_GHI():
    test_solar_calculations = simulation.SolarCalculations()

    test_latitude = 40
    test_longitude = -95
    test_time_zone_utc = -5
    test_local_time = 13
    test_elevation = 300
    test_cloud_cover = 4.5

    test_days_of_year = np.array([2, 4, 6, 20, 40, 60, 120, 140, 160, 180, 240, 260, 280, 318, 358])

    expected_GHI_vals = np.array([399.5830603, 402.2365993, 405.3290578, 438.8673503, 518.6521095, 623.4173354,
                                  898.807351, 940.6022924, 959.3052252, 960.0064743, 849.1084979, 763.5088187,
                                  659.1287756, 504.4161605, 393.1428821])

    test_GHI_vals = np.array([])
    for day in test_days_of_year:
        test_GHI_vals.np.append(test_solar_calculations.calculate_GHI(test_latitude, test_longitude,
                                                                      test_time_zone_utc, day, test_local_time,
                                                                      test_elevation, test_cloud_cover))

    assert (True == np.allclose(test_GHI_vals, expected_GHI_vals, rtol=1e-05, atol=1e-06))


if __name__ == "__main__":
    pass
    # test_calculate_declination_angle()
    # test_calculate_azimuth_angle()
    # test_calculate_GHI()
    # test_calculate_elevation_angle()
    # test_calculate_zenith_angle()

import numpy as np
import os
import pytest
import simulation
from dotenv import load_dotenv
from simulation.common import helpers
from simulation.common.constants import EARTH_RADIUS


@pytest.fixture
def gis():
    # Initialises the GIS object as a PyTest fixture so it can be used in all subsequent test functions

    load_dotenv()

    google_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

    origin_coord = np.array([39.0918, -94.4172])

    waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

    dest_coord = np.array([43.6142, -116.2080])

    location_system = simulation.environment.GIS(api_key=google_api_key, origin_coord=origin_coord,
                                                 waypoints=waypoints, dest_coord=dest_coord, race_type="ASC")

    return location_system


def test_calculate_closest_gis_indices(gis):
    test_cumulative_distances = np.array([0, 9, 18, 19, 27, 35, 38, 47, 48, 56, 63])
    test_path_distances = np.repeat(20, 13)
    test_path_distances[0] = 0

    gis.path_distances = test_path_distances

    result = gis.calculate_closest_gis_indices(test_cumulative_distances)

    assert np.all(result == np.array([0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3]))


def test_get_time_zones(gis):
    test_coord = np.tile([39.0918, -94.4172], 625 * 2)

    # Expected time zone checked on https://timezonedb.com/
    expected_time_zone = np.full(len(test_coord), -18000.)

    test_coord_cumulative_distances = np.cumsum(test_coord)

    test_coord_closest_gis_indices = gis.calculate_closest_gis_indices(
        cumulative_distances=test_coord_cumulative_distances)
    result = gis.get_time_zones(test_coord_closest_gis_indices)

    assert len(test_coord) == len(expected_time_zone)
    assert np.all(result == expected_time_zone)


def test_adjust_timestamps_to_local_times(gis):
    test_timestamps = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    test_starting_drive_time = 10.0
    test_time_zones = np.append(np.repeat(-18000, 4), np.repeat(-21600, 6))
    expected_local_times = np.array(np.append(np.arange(10, 14), np.arange(-3600 + 14, -3600 + 20)), dtype=np.uint64)

    result = helpers.adjust_timestamps_to_local_times(test_timestamps, test_starting_drive_time, test_time_zones)
    assert np.all(result == expected_local_times)


def test_calculate_path_distances():
    test_coord = np.array([[43., -116], [43., -116.]])
    expected_path_distance = np.array([0.0])

    result = helpers.calculate_path_distances(test_coord)
    assert np.all(result == expected_path_distance)


def test_calculate_path_distances1():
    test_coord = np.array([[43., -116], [43.002, -116.003]])

    offset = np.roll(test_coord, (1, 1))
    diff = (test_coord - offset)[1:] * np.pi / 180
    diff_lat, diff_lng = np.split(diff, 2, axis=1)
    diff_lat = np.squeeze(diff_lat)
    diff_lng = np.squeeze(diff_lng)
    mean_lat = ((test_coord + offset)[1:, 0] * np.pi / 180) / 2
    diff_lng_adjusted = np.cos(mean_lat) * diff_lng
    square_sum = np.square(diff_lat) + np.square(diff_lng_adjusted)

    expected_path_distance = EARTH_RADIUS * np.sqrt(square_sum)
    result = helpers.calculate_path_distances(test_coord)
    assert np.all(result == expected_path_distance)


def test_calculate_path_distances2():
    test_coord = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                           [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                           [42.3224, -111.2973], [42.5840, -114.4703]])

    offset = np.roll(test_coord, (1, 1))
    diff = (test_coord - offset)[1:] * np.pi / 180
    diff_lat, diff_lng = np.split(diff, 2, axis=1)
    diff_lat = np.squeeze(diff_lat)
    diff_lng = np.squeeze(diff_lng)
    mean_lat = ((test_coord + offset)[1:, 0] * np.pi / 180) / 2
    diff_lng_adjusted = np.cos(mean_lat) * diff_lng
    square_sum = np.square(diff_lat) + np.square(diff_lng_adjusted)

    expected_path_distance = EARTH_RADIUS * np.sqrt(square_sum)
    result = helpers.calculate_path_distances(test_coord)
    assert np.all(result == expected_path_distance)


def test_calculate_path_gradients1():
    test_elevations = np.arange(10.)

    test_distances = np.repeat(20, 9)
    gis.path_distances = test_distances

    expected_gradients = np.repeat(0.05, 9)

    result = helpers.calculate_path_gradients(test_elevations, test_distances)
    assert np.all(result == expected_gradients)


def test_calculate_path_gradients2(gis):
    test_elevations = np.append(np.arange(10.), np.arange(10, 0, -1))

    test_distances = np.append(np.repeat(20, 5), np.repeat(10, 14))
    gis.path_distances = test_distances

    expected_gradients = np.array([0.05, 0.05, 0.05, 0.05, 0.05,
                                   0.1, 0.1, 0.1, 0.1, 0.1,
                                   -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, ])
    result = helpers.calculate_path_gradients(test_elevations, test_distances)
    assert np.all(result == expected_gradients)


if __name__ == "__main__":
    pass

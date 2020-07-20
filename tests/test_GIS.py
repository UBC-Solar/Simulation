import simulation
import numpy as np


def test_calculate_closest_gis_indices():
    cumulative_distances = np.array([0, 9, 18, 19, 27, 35, 38, 47, 48, 56, 63])
    cumulative_path_distances = np.linspace(0, 240, num=13)

    google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"

    origin_coord = np.array([39.0918, -94.4172])

    waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

    dest_coord = np.array([43.6142, -116.2080])

    locationSystem = simulation.environment.GIS(api_key=google_api_key, origin_coord=origin_coord,
                                                waypoints=waypoints, dest_coord=dest_coord)

    locationSystem.path_distances = cumulative_path_distances

    result = locationSystem.calculate_closest_gis_indices(cumulative_distances)

    assert np.all(result == np.array([0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3]))

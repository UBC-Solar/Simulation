import simulation
import numpy as np

google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"

simulation_duration = 60 * 60 * 9

origin_coord = np.array([39.0918, -94.4172])

waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

dest_coord = np.array([43.6142, -116.2080])

gis = simulation.GIS(google_api_key, origin_coord, dest_coord, waypoints)
route_coords = gis.get_path()

weather_api_key = "51bb626fa632bcac20ccb67a2809a73b"

localWeather = simulation.WeatherForecasts(weather_api_key, route_coords, simulation_duration)


def test_calculate_closest_weather_indices():
    test_cumulative_distances = np.array([0, 9, 18, 19, 27, 35, 38, 47, 48, 56, 63])*1000
    test_weather_forecast = np.zeros((11,8,9))

    for i in range(11):
        test_weather_forecast[i, 0, 0:2] = np.array([39.,-94.-.23145*i])
   #testing path distances
    test_coord = np.zeros((11, 2))
    for i in range(11):
        test_coord[i, 0:2] = np.array([39, -94 - .23145 * i])

    expected_path_distance = np.repeat(20, 10) * 1000
    result = localWeather.calculate_path_distances(test_coord)
    assert np.allclose(result, expected_path_distance, atol=1)

    expected_closest_weather_indices = np.array([0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3])
    localWeather.weather_forecast = test_weather_forecast
    result = localWeather.calculate_closest_weather_indices(test_cumulative_distances)
    assert np.all(result == expected_closest_weather_indices)


if __name__ == "__main__":
    test_calculate_closest_weather_indices()
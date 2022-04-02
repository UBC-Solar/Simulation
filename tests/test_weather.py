import dotenv
import os
import pytest
import simulation
from simulation.common.helpers import *
from simulation.environment import WeatherForecasts


@pytest.fixture
def weather():
    dotenv.load_dotenv()

    weather_api_key = os.environ.get("OPENWEATHER_API_KEY")
    google_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

    origin_coord = np.array([39.0918, -94.4172])

    waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

    dest_coord = np.array([43.6142, -116.2080])

    location_system = simulation.environment.GIS(api_key=google_api_key, origin_coord=origin_coord,
                                                 waypoints=waypoints, dest_coord=dest_coord, race_type="ASC")

    route_coords = location_system.get_path()

    # 5 day simulation duration
    simulation_duration = 432000

    weather_calculations = simulation.environment.WeatherForecasts(api_key=weather_api_key,
                                                                   coords=route_coords,
                                                                   duration=simulation_duration / 3600,
                                                                   race_type="ASC",
                                                                   force_update=False)

    return weather_calculations


def test_compare_golang_python_get_weather_in_time(weather):
    """

    Unit test for WeatherForecasts.golang_calculate_closest_timestamp_indices and
    WeatherForecasts.python_calculate_closest_timestamp_indices.
    Checks to see if the results are the same format and equal element-wise

    """

    dt_local_array = [1.6463088e+09, 1.6463952e+09, 1.6464816e+09,
                      1.6465680e+09, 1.6466544e+09, 1.6467408e+09, 1.6468272e+09, 1.6469136e+09]
    unix_timestamps = [i for i in range(1646377200, 1646636400 + 1)]

    go_gwit_result = weather.golang_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array)

    python_gwit_result = weather.python_calculate_closest_timestamp_indices(unix_timestamps, dt_local_array)

    assert np.all(go_gwit_result == python_gwit_result)

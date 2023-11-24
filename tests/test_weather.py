import dotenv
import os
import pytest
import simulation
from simulation.common.helpers import *
from simulation.environment import WeatherForecasts
from simulation.library import libraries


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
                                                 waypoints=waypoints, dest_coord=dest_coord, race_type="ASC",
                                                 golang=False)

    route_coords = location_system.get_path()

    # 5 day simulation duration
    simulation_duration = 432000
    library = libraries.Libraries()
    weather_calculations = simulation.environment.WeatherForecasts(api_key=weather_api_key,
                                                                   coords=route_coords,
                                                                   duration=simulation_duration / 3600,
                                                                   race_type="ASC",
                                                                   force_update=False,
                                                                   golang=True,
                                                                   library=library)

    return weather_calculations

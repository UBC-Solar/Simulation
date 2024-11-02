import pytest

from simulation.cmd.run_simulation import RaceDataNotMatching
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.model.Simulation import SimulationReturnType
from simulation.common.race import Race
from simulation.utils.hash_util import hash_dict
import numpy as np

def test_consistent_race_data():
    """
        Tests that a Simulation is created successfully when race data matches the expected model parameters.

        Asserts that the SimulationBuilder successfully generates a Simulation object
        when consistent data is provided, without raising exceptions.
        """
    data = (
        {
            "race_type": "FSGP",
            "origin_coord": [38.9281815, -95.677021],
            "dest_coord": [38.9282115, -95.6770268],
            "waypoints": [
                [36.99932082, -86.37230251],
                [36.99924349, -86.37245211],
                [36.99932082, -86.37230251]
            ],
            "tick": 10,
            "race_length": 0,
            "lvs_power_loss": 0,
            "period": "5min",
            "weather_freq": "daily",
            "weather_provider": "OPENWEATHER",
            "days": {
                "0": {
                    "charging": [25200, 72000],
                    "driving": [36000, 57600]
                },
                "1": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                },
                "2": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                }
            },
            "tiling": 200,
            "start_year": 2024,
            "start_month": 7,
            "start_day": 15
        },
        {
            "current_coord": [
                38.9281815,
                -95.677021
            ],
            "start_time": 67113,
            "initial_battery_charge": 0.99,
            "timezone_offset": 7200.0
        }
    )

    route = (
        {'path': [[36.99932082, -86.37230251],
                        [36.99940337, -86.37214797],
                        [36.99924349, -86.37245211]],
         'elevations': [156.47387695],
         'time_zones': [-18000., -18000., -18000., -18000., -18000., -18000.],
         'origin_coord': [38.9281815, -95.677021], 'dest_coord': [38.9282115, -95.6770268],
         'speed_limits': [76, 76, 76, 57, 57, 57], 'waypoints': [[36.99932082, -86.37230251],
                                                                                   [36.99940337, -86.37214797],
                                                                                   [36.99932082, -86.37230251]],
         'hash': 'a6784b4eac6b948f2109a2a4cddc46a728a91c9c10fb237b0cef7b7a6eaf1541',
                       'num_unique_coords': 289}
    )

    weather = [
        [
            [1721102100, 36.9993208, -86.3723025, 27.0, 215.0, 0.0],  # First group, first record
            [1721102400, 36.9993208, -86.3723025, 27.0, 214.0, 0.0],  # First group, second record
            [1721102700, 36.9993208, -86.3723025, 27.0, 214.0, 0.0]  # First group, third record
        ],
        [
            [1721285100, 36.9993208, -86.3723025, 12.0, 333.0, 0.0],  # Second group, first record
            [1721285400, 36.9993208, -86.3723025, 12.0, 332.0, 0.0],  # Second group, second record
            [1721285700, 36.9993208, -86.3723025, 11.0, 332.0, 0.0]  # Second group, third record
        ],
        [
            [1721300000, 36.9993208, -86.3723025, 10.0, 320.0, 0.0],  # Third group, first record
            [1721310000, 36.9993208, -86.3723025, 9.5, 310.0, 0.0],  # Third group, second record
            [1721320000, 36.9993208, -86.3723025, 9.0, 305.0, 0.0]  # Third group, third record
        ]
    ]
    weather_np = np.array(weather)

    model_parameters, initial_conditions = data
    race = Race(Race.FSGP, model_parameters)

    # No error raise expected
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.FSGP) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(1) \
        .set_race_data(race) \
        .set_route_data(route) \
        .set_weather_forecasts(weather_np)
    simulation_builder.get()



def test_inconsistent_race_data():
    """
        Tests that a RaceDataNotMatching exception is raised for inconsistent race data.

        Ensures that when the provided race data does not match the expected model parameters,
        the SimulationBuilder raises the appropriate exception.
        """
    data = (
        {
            "race_type": "FSGP",
            "origin_coord": [38.9281815, -95.677021],
            "dest_coord": [38.9282115, -95.6770268],
            "waypoints": [
                [36.99932082, -86.37230251],
                [36.99924349, -86.37245211],
                [36.99932082, -86.37230251]
            ],
            "tick": 10,
            "race_length": 0,
            "lvs_power_loss": 0,
            "period": "5min",
            "weather_freq": "daily",
            "weather_provider": "OPENWEATHER",
            "days": {
                "0": {
                    "charging": [25200, 72000],
                    "driving": [36000, 57600]
                },
                "1": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                },
                "2": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                }
            },
            "tiling": 200,
            "start_year": 2024,
            "start_month": 7,
            "start_day": 15
        },
        {
            "current_coord": [
                38.9281815,
                -95.677021
            ],
            "start_time": 67113,
            "initial_battery_charge": 0.99,
            "timezone_offset": 7200.0
        }
    )
    data2 = (
        {
            "race_type": "FSGP",
            "origin_coord": [38.9281815, -95.677021],
            "dest_coord": [38.9282115, -95.6770268],
            "waypoints": [
                [36.99932082, -86.37230251],
                [36.99924349, -86.37245211],
                [36.99936772082, -86.37867230251]
            ],
            "tick": 10,
            "race_length": 66,
            "lvs_power_loss": 0,
            "period": "5min",
            "weather_freq": "daily",
            "weather_provider": "OPENWEATHER",
            "days": {
                "0": {
                    "charging": [25200, 72000],
                    "driving": [36000, 57600]
                },
                "1": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                },
                "2": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                }
            },
            "tiling": 2060,
            "start_year": 20624,
            "start_month": 67,
            "start_day": 15
        },
        {
            "current_coord": [
                38.9281815,
                -95.677021
            ],
            "start_time": 67113,
            "initial_battery_charge": 0.99,
            "timezone_offset": 7200.0
        }
    )
    route = (
        {'path': [[36.99932082, -86.37230251],
                  [36.99940337, -86.37214797],
                  [36.99924349, -86.37245211]],
         'elevations': [156.47387695],
         'time_zones': [-18000., -18000., -18000., -18000., -18000., -18000.],
         'origin_coord': [38.9281815, -95.677021], 'dest_coord': [38.9282115, -95.6770268],
         'speed_limits': [76, 76, 76, 57, 57, 57], 'waypoints': [[36.99932082, -86.37230251],
                                                                 [36.99940337, -86.37214797],
                                                                 [36.99932082, -86.37230251]],
         'hash': 'a6784b4eac6b948f2109a2a4cddc46a728a91c9c10fb237b0cef7b7a6eaf1541',
         'num_unique_coords': 289}
    )

    weather = [
        [
            [1721102100, 36.9993208, -86.3723025, 27.0, 215.0, 0.0],  # First group, first record
            [1721102400, 36.9993208, -86.3723025, 27.0, 214.0, 0.0],  # First group, second record
            [1721102700, 36.9993208, -86.3723025, 27.0, 214.0, 0.0]  # First group, third record
        ],
        [
            [1721285100, 36.9993208, -86.3723025, 12.0, 333.0, 0.0],  # Second group, first record
            [1721285400, 36.9993208, -86.3723025, 12.0, 332.0, 0.0],  # Second group, second record
            [1721285700, 36.9993208, -86.3723025, 11.0, 332.0, 0.0]  # Second group, third record
        ],
        [
            [1721300000, 36.9993208, -86.3723025, 10.0, 320.0, 0.0],  # Third group, first record
            [1721310000, 36.9993208, -86.3723025, 9.5, 310.0, 0.0],  # Third group, second record
            [1721320000, 36.9993208, -86.3723025, 9.0, 305.0, 0.0]  # Third group, third record
        ]
    ]

    weather_np = np.array(weather)
    model_parameters, initial_conditions = data
    model_parameters2, initial_conditions2 = data2
    race = Race(Race.FSGP, model_parameters)

    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions2) \
        .set_model_parameters(model_parameters2, Race.FSGP) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(1) \
        .set_race_data(race) \
        .set_route_data(route) \
        .set_weather_forecasts(weather_np)

    with pytest.raises(RaceDataNotMatching):
        simulation_builder.get()

def testHash():
    """
        Tests the consistency and uniqueness of the hash generation for race data.

        Verifies that the same input data produces consistent hashes and different inputs
        result in distinct hashes, ensuring data integrity checks.
        """
    input = (
        {
          "race_type": "FSGP",
          "origin_coord": [
            38.9281815,
            -95.677021
          ],
          "dest_coord": [
            38.9282115,
            -95.6770268
          ],
          "waypoints": [
            [ 36.99932082, -86.37230251],
            [ 36.99924349, -86.37245211],
            [ 36.99932082, -86.37230251]
          ],

          "tick": 10,
          "race_length": 0,
          "lvs_power_loss": 0,

          "period": "5min",
          "weather_freq": "daily",
          "weather_provider": "OPENWEATHER",

          "days": {
            "0": {
              "charging": [25200, 72000],
              "driving": [36000, 57600]
            },
            "1": {
              "charging": [25200, 72000],
              "driving": [32400, 61200]
            },
            "2": {
              "charging": [25200, 72000],
              "driving": [32400, 61200]
            }
          },
          "tiling": 200,
          "start_year": 2024,
          "start_month": 7,
          "start_day": 15
        }
    )
    input2 = (
        {
            "race_type": "FSGP",
            "origin_coord": [
                38.9281815,
                -95.6767021
            ],
            "dest_coord": [
                38.9282115,
                -95.6770268
            ],
            "waypoints": [
                [36.99932082, -86.37230251],
                [36.99924349, -86.37245211],
                [36.99932082, -86.37230251]
            ],

            "tick": 10,
            "race_length": 0,
            "lvs_power_loss": 0,

            "period": "5min",
            "weather_freq": "daily",
            "weather_provider": "OPENWEATHER",

            "days": {
                "0": {
                    "charging": [25200, 72000],
                    "driving": [36000, 57600]
                },
                "1": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                },
                "2": {
                    "charging": [25200, 72000],
                    "driving": [32400, 61200]
                }
            },
            "tiling": 200,
            "start_year": 2024,
            "start_month": 7,
            "start_day": 15
        }
    )

    model_parameters2 = input
    hashed1 = hash_dict(model_parameters2)

    assert (hash_dict(model_parameters2) == hashed1)
    assert (hash_dict(input2) != hash_dict(model_parameters2))



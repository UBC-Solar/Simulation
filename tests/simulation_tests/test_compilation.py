import pytest

from simulation.cmd.run_simulation import RaceDataNotMatching
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.model.Simulation import Simulation, SimulationReturnType
from simulation.common.race import Race

def test_consistent_race_data():
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

    model_parameters, initial_conditions = data
    race = Race(Race.FSGP, model_parameters)

    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.FSGP) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(1) \
        .set_race_data(race)
    simulation_builder.get()


def test_inconsistent_race_data():
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
    model_parameters, initial_conditions = data
    model_parameters2, initial_conditions2 = data2
    race = Race(Race.FSGP, model_parameters)

    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions2) \
        .set_model_parameters(model_parameters2, Race.FSGP) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(1) \
        .set_race_data(race)

    with pytest.raises(RaceDataNotMatching):
        simulation_builder.get()
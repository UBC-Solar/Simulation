import pytest
from simulation.utils.SimulationBuilder import SimulationBuilder
from simulation.model.Simulation import Simulation, SimulationReturnType
from physics.environment.race import Race

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
            "weather_provider": "OPENWEATHER"
        },
        {
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
    Race("FSGP", data)
    initial_conditions, model_parameters = data
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.RaceType(race_type)) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(granularity)
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
            "weather_provider": "OPENWEATHER"
        },
        {
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
    data2 = (
        {
            "race_type": "FSGP",
            "origin_coord": [38.9281815, -95.677021],
            "dest_coord": [38.92821478938389983489458915, -95.6770268],
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
            "weather_provider": "OPENWEATHER"
        },
        {
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
    Race("FSGP", data2)
    initial_conditions, model_parameters = data
    simulation_builder = SimulationBuilder() \
        .set_initial_conditions(initial_conditions) \
        .set_model_parameters(model_parameters, Race.RaceType(race_type)) \
        .set_return_type(SimulationReturnType.void) \
        .set_granularity(granularity)

    with pytest.raises(RaceConstantsInconsistentError):
        simulation_builder.get()
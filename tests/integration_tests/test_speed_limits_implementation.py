import numpy as np
import core
import argparse
from dotenv import load_dotenv
import sys
from simulation.cmd.run_simulation import SimulationSettings
from unittest import mock
from simulation.cmd.run_simulation import build_model
from simulation.common import helpers

# load API keys from environment variables
load_dotenv()


def test_speed_limits_high_speed():
    """Testing that the new data-driven speed limit implementation works when using the command run_simulation.
    In this particular instance, we feed a speed array where every value is higher than the highest speed limit,
    which is 72.74 km/hr. Therefore, we expect all speeds to be constrained.
    """

    test_args = ["script.py", "--race_type", "FSGP", "--granularity", "2", "--verbose"]
    with mock.patch.object(sys, 'argv', test_args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--race_type", required=False, default="FSGP",
                            help="Define which race should be simulated. (ASC/FSGP)", type=str)
        parser.add_argument("--granularity", required=False, default=1,
                            help="Define how granular the speed array should be, where 1 is hourly and 2 is bi-hourly.",
                            type=int)
        parser.add_argument("-v", "--verbose", required=False, default=False,
                            help="Set to make simulation execute as verbose.", action="store_true")

        args = parser.parse_args()

        # Making sure that the race settings are correct
        assert args.race_type == "FSGP"
        assert args.granularity == 2
        assert args.verbose is True

        settings = SimulationSettings(race_type=args.race_type, verbose=args.verbose, granularity=args.granularity)

        simulation_model = build_model(settings)
        driving_hours = simulation_model.get_driving_time_divisions()

        # Setting all speeds to be higher than the highest speed limit
        speed = np.array([75] * driving_hours)
        assert np.all(speed == 75), "Not all values in speed are 75."

        # Note: reshape_speed_array returns an array of a different length and sets speed to zero when not driving
        speed_kmh = helpers.reshape_speed_array(
            simulation_model.race,
            speed,
            simulation_model.granularity,
            simulation_model.start_time,
            simulation_model.tick
        )

        # ----- Preserve raw speed -----
        raw_speed = speed_kmh.copy()
        speed_kmh = core.constrain_speeds(
            simulation_model.route_data["speed_limits"].astype(float),
            speed_kmh,
            simulation_model.tick
        )

        # Testing that the max value in raw_speed is 75
        assert max(raw_speed) == 75, "The maximum value in raw_speed should be 75."

        # Testing that all values in speed_kmh are less than 75, i.e., they have been constrained
        assert np.all(speed_kmh < 75)

def test_speed_limits_low_speed():
    """We feed a speed array where every value is lower than the lowest speed limit,
    which is 45.4 km/hr. Therefore, we expect none of the speeds to be constrained."""

    test_args = ["script.py", "--race_type", "FSGP", "--granularity", "2", "--verbose"]
    with (mock.patch.object(sys, 'argv', test_args)):
        parser = argparse.ArgumentParser()
        parser.add_argument("--race_type", required=False, default="FSGP",
                            help="Define which race should be simulated. (ASC/FSGP)", type=str)
        parser.add_argument("--granularity", required=False, default=1,
                            help="Define how granular the speed array should be, where 1 is hourly and 2 is bi-hourly.",
                            type=int)
        parser.add_argument("-v", "--verbose", required=False, default=False,
                            help="Set to make simulation execute as verbose.", action="store_true")

        args = parser.parse_args()

        # Making sure that the race settings are correct
        assert args.race_type == "FSGP"
        assert args.granularity == 2
        assert args.verbose is True

        settings = SimulationSettings(race_type=args.race_type, verbose=args.verbose, granularity=args.granularity)

        simulation_model = build_model(settings)
        driving_hours = simulation_model.get_driving_time_divisions()

        # Setting all speeds to be lower than the lowest speed limit
        speed = np.array([40] * driving_hours)

        assert np.all(speed == 40), "Not all values in speed are 40."

        # Note: reshape_speed_array returns an array of a different length and sets speed to zero when not driving
        speed_kmh = helpers.reshape_speed_array(simulation_model.race, speed, simulation_model.granularity, simulation_model.start_time, simulation_model.tick)

        # ----- Preserve raw speed -----
        raw_speed = speed_kmh.copy()
        speed_kmh = core.constrain_speeds(simulation_model.route_data["speed_limits"].astype(float), speed_kmh, simulation_model.tick)

        # Testing that the max value in raw_speed is 75
        assert max(raw_speed) == 40

        # Testing that the speed has not been changed
        assert np.array_equal(raw_speed, speed_kmh)
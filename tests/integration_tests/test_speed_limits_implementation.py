import pytest
import numpy as np
import core
import argparse
from dotenv import load_dotenv
from simulation.utils import Query
import sys
from simulation.cmd.run_simulation import SimulationSettings
from unittest import mock
from simulation.cmd.run_simulation import build_model

# load API keys from environment variables
load_dotenv()


def test_example():
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

        assert args.race_type == "FSGP"
        assert args.granularity == 2
        assert args.verbose is True

        settings = SimulationSettings(race_type=args.race_type, verbose=args.verbose, granularity=args.granularity)

        simulation_model = build_model(settings)
        driving_hours = simulation_model.get_driving_time_divisions()

        speeds = np.array([45] * driving_hours)

        speed_kmh = helpers.reshape_speed_array(self.race, speed, self.granularity, self.start_time, self.tick)

        # ----- Preserve raw speed -----
        raw_speed = speed_kmh.copy()
        speed_kmh = core.constrain_speeds(self.route_data["speed_limits"].astype(float), speed_kmh, self.tick)





import simulation
from simulation.common import helpers
from simulation.simulation_types import *
import numpy as np


class ASC_Simulation(BaseSimulation):
    def __init__(self, input_speed, start_hour, simulation_duration):
        super().__init__()

        # ----- Route Definition -----
        self.origin_coord = np.array([39.0918, -94.4172])

        self.waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                                   [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                                   [42.3224, -111.2973], [42.5840, -114.4703]])

        self.dest_coord = np.array([43.6142, -116.2080])

        self.input_speed = input_speed

        # ----- Race-Specific Timing Constants -----

        self.simulation_duration = simulation_duration
        self.start_hour = start_hour

        # ----- Configure
        self.configure_race("ASC")

    def run_model(self):
        pass

    def __str__(self):
        return "ASC"


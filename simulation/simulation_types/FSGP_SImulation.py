import simulation
from simulation.common import helpers
from simulation.simulation_types import BaseSimulation
import numpy as np


class FSGP_Simulation(BaseSimulation):

    """
    Instantiates an FSGP_Simulation object that models the 2021 FSGP Race

    :param input_speed:
    :param:

    """
    def __init__(self, input_speed, start_hour, simulation_duration):
        super().__init__()
        # ----- Route Definition -----
        self.origin_coord = np.array([38.9266274, -95.6781231])

        self.waypoints = np.array([[38.9253374, -95.678453], [38.921052, -95.674689],
                                   [38.9206115, -95.6784807], [38.9211163, -95.6777508],
                                   [38.9233953, -95.6783869]])

        self.dest_coord = np.array([38.9219577, -95.6776967])

        self.input_speed = input_speed

        # ----- Race-Specific Timing Constants -----

        self.simulation_duration = simulation_duration
        self.start_hour = start_hour

        self.configure_race("FSGP")

    def run_model(self):
        pass

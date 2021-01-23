from simulation.simulation_types import *
import numpy as np
from simulation.simulation_types.ASC_Simulation import ASC_Simulation
from simulation.simulation_types.FSGP_SImulation import FSGP_Simulation


class Simulation:
    def __init__(self, race_type):
        # length of the simulation in seconds
        simulation_length = 60 * 60 * 12  # 10 hours -> seconds

        # Input Parameters
        input_speed = np.array([35] * 12)
        start_hour = 3
        self.race_type = race_type

        if self.race_type == "ASC":
            self.model = ASC_Simulation(input_speed, start_hour, simulation_length)
        elif self.race_type == "FSGP":
            self.model = FSGP_Simulation(input_speed, start_hour, simulation_length)
        else:
            raise Exception("race_type argument must be one of \"FSGP\" or \"ASC\". ")

import numpy as np
from simulation.simulation_types.ASC_Simulation import ASC_Simulation
from simulation.simulation_types.FSGP_SImulation import FSGP_Simulation


class Simulation:
    """
    Wrapper class to interact with  ASC_Simulation and FSGP_Simulation Objects

    :param race_type: string representing type of race to simulate
    :throws Exception: if race type argument is not one of "ASC" or "FSGP"
    """
    def __init__(self, race_type):

        # Input Parameters
        input_speed = np.array([35] * 12)

        # May move start_hour and simulation_length into ASC/FSGP classes
        # (May be race specific) but keeping it here for testing
        start_hour = 9
        simulation_length = 60 * 60 * 12  # length of the simulation in seconds

        if race_type == "ASC":
            self.model = ASC_Simulation(input_speed, start_hour, simulation_length)
        elif race_type == "FSGP":
            self.model = FSGP_Simulation(input_speed, start_hour, simulation_length)
        else:
            raise Exception("race_type argument must be one of \"FSGP\" or \"ASC\". ")

    """
    Effect: Starts the simulation, plots results, and displays plot on screen
    """

    def run_model(self):
        self.model.run_model(plot_results=True)

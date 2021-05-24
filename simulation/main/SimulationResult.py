from collections import OrderedDict


class SimulationResult:
    def __init__(self, array_dict: OrderedDict, time_taken: str, distance_travelled: float, average_speed: float,
                 final_soc: float):
        """
        Instantiates a SimulationResult object. This is used in the MainSimulation class when
        running a simulation. This object simply stores desired simulation results while the
        simulation is running its calculations to better encapsulate the information
        """
        self.array_dict = array_dict
        self.time_taken = time_taken
        self.distance_travelled = distance_travelled
        self.average_speed = average_speed
        self.final_soc = final_soc
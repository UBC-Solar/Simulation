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

    def __str__(self):
        return(f"<----- Simulation result ----->\n"
               f"Array dict keys: {list(self.array_dict.keys())}\n"
               f"Time taken: {self.time_taken}\n"
               f"Maximum distance traversable: {self.distance_travelled:.2f}km\n"
               f"Average speed: {self.average_speed:.2f}km/h\n"
               f"Final battery SOC: {self.final_soc:.2f}%\n")

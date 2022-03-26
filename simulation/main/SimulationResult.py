class SimulationResult:
    def __init__(self, arrays=None, distance_travelled=None, time_taken=None, final_soc=None):
        """
        Instantiates a SimulationResult object. This is used in the MainSimulation class when
        running a simulation. This object simply stores desired simulation results while the
        simulation is running its calculations to better encapsulate the information
        """
        self.arrays = arrays
        self.distance_travelled = distance_travelled
        self.time_taken = time_taken
        self.final_soc = final_soc

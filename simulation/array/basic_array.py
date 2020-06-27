from simulation.array.base_array import BaseArray


class BasicArray(BaseArray):

    # incident_sunlight:
    def __init__(self, incident_sunlight):
        super().__init__()

        self.sunlight = incident_sunlight
        self.panel_efficiency = 0.2
        self.panel_size = 6

    @staticmethod
    def calculate_produced_power(sunlight, panel_efficiency, panel_size):
        produced_power = sunlight * panel_efficiency * panel_size
        return produced_power

    def update(self, tick):
        """
        updates model for a single tick

        :param tick: (float) the length of time for the tick (in seconds)

        """

        # Assume constant sunlight in this simple model.
        self.produced_energy = self.calculate_produced_power(self.sunlight,
                                        self.panel_efficiency, self.panel_size) * tick

    def __str__(self):
        return(f"BasicArray: incident_sunlight: {self.sunlight}W/m^2\n"
               f"BasicArray: panel_size: {self.panel_size}m^2\n"
               f"BasicArray: panel_efficiency: {self.panel_efficiency * 100}%\n")

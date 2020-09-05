from simulation.array.base_array import BaseArray


class BasicArray(BaseArray):

    # incident_sunlight:
    def __init__(self):
        super().__init__()

        # solar cell efficiency
        self.panel_efficiency = 0.2

        # solar panel size in m^2
        self.panel_size = 6

        # please do not use this.
        self.solar_irradiance = 1200

    @staticmethod
    def calculate_produced_power(solar_irradiance, panel_efficiency, panel_size):
        """
        returns the power produced by a solar panel in watts

        :param solar_irradiance: (float) a value for global horizontal irradiance (GHI)
            in W/m2
        :param panel_efficiency: (float) the efficiency of the solar cells as a number
            between 0 and 1, in atmosphere and with sunlight.
        :param panel_size: (float) the area of the solar panels in m2
        
        :returns: the power produced by a solar panel in W
        """

        produced_power = solar_irradiance * panel_efficiency * panel_size

        return produced_power

    def update(self, tick):
        """
        updates solar array model for a single tick

        :param tick: (float) the length of time for the tick (in seconds)

        note: do not use this please. Use calculate_produced_energy instead.
        """

        # Assume constant sunlight in this simple model.
        self.produced_energy = self.calculate_produced_power(self.solar_irradiance,
                                                             self.panel_efficiency, self.panel_size) * tick

    def calculate_produced_energy(self, solar_irradiance, tick):
        """
        returns a numpy array with the energy produced by the solar panels across
        each the length of each tick

        :param solar_irradiance: (float[N]) the global horizontal irradiance(GHI) at
            each moment experienced by the vehicle, in W/m2
        :param tick: (float) the duration of a time step in seconds

        returns: (float[N]) array of energy produced by the solar panels on the vehicle
            in Joules
        """

        return solar_irradiance * self.panel_efficiency * self.panel_size * tick

    def __str__(self):
        return(f"BasicArray: incident_sunlight: {self.solar_irradiance}W/m^2\n"
               f"BasicArray: panel_size: {self.panel_size}m^2\n"
               f"BasicArray: panel_efficiency: {self.panel_efficiency * 100}%\n")

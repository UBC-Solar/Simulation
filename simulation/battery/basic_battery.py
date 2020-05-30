from simulation.battery.base_battery import BaseBattery
from numpy.polynomial import Polynomial


class BasicBattery(BaseBattery):
    """
    Class representing the DayBreak battery pack.

    Attributes:
        max_voltage (float): maximum voltage of the DayBreak battery pack (V)
        min_voltage (float): minimum voltage of the DayBreak battery pack (V)
        max_current_capacity (float): nominal capacity of the DayBreak battery pack (Ah)
        max_energy_capacity (float): nominal energy capacity of the DayBreak battery pack (Wh)

        state_of_charge (float): instantaneous battery state-of-charge (0.00 - 1.00)
        depth_of_discharge (float): inverse of battery state-of-charge (0.00 - 1.00)
        discharge_capacity (float): instantaneous amount of charge extracted from battery (Ah)
        voltage (float): instantaneous voltage of the battery (V)
        stored_energy (float): instantaneous energy stored in the battery (Wh)
    """

    def __init__(self, state_of_charge):
        """
        Constructor for BasicBattery class.

        :param state_of_charge: initial battery state of charge
        """

        # ----- DayBreak battery constants -----

        self.max_voltage = 117.6
        self.min_voltage = 75.6
        self.max_current_capacity = 48.9
        self.max_energy_capacity = 4723.74

        # ----- DayBreak battery equations -----

        self.calculate_voltage_from_discharge_capacity = Polynomial([117.6, -0.858896])    # -0.97641x + 117.6

        self.calculate_energy_from_discharge_capacity = Polynomial([0, 117.6, -0.429448])    # -0.488x^2 + 117.6x

        self.calculate_soc_from_discharge_capacity = Polynomial([1, -1 / self.max_current_capacity])

        self.calculate_discharge_capacity_from_soc = Polynomial([self.max_current_capacity, -self.max_current_capacity])

        # ----- DayBreak battery variables -----

        self.state_of_charge = state_of_charge
        self.depth_of_discharge = 1 - self.state_of_charge

        # SOC -> discharge_capacity
        self.discharge_capacity = self.calculate_discharge_capacity_from_soc(self.state_of_charge)

        # discharge_capacity -> voltage
        self.voltage = self.calculate_voltage_from_discharge_capacity(self.discharge_capacity)

        # discharge_capacity -> energy
        self.stored_energy = self.max_energy_capacity - self.calculate_energy_from_discharge_capacity(
            self.discharge_capacity)

        # ----- DayBreak battery initialisation -----

        super().__init__(self.stored_energy, self.max_current_capacity, self.max_energy_capacity,
                         self.max_voltage, self.min_voltage, self.voltage, self.state_of_charge)

    def update(self, tick):
        """
        Updates battery variables according to energy changes.

        :param tick: time interval (in seconds) for battery variable update (dt)
        """

        energy_discharged = self.max_energy_capacity - self.stored_energy
        discharge_capacity = (self.calculate_energy_from_discharge_capacity - energy_discharged).roots()[0]

        self.state_of_charge = self.calculate_soc_from_discharge_capacity(discharge_capacity)
        self.voltage = self.calculate_voltage_from_discharge_capacity(discharge_capacity)

    def charge(self, energy):
        """
        Adds energy to the battery.

        :param energy: energy (in joules) to be added to battery.
        """

        # divide by 3600 to convert from joules to watt-hours
        super().charge(energy / 3600)

    def discharge(self, energy):
        """
        Takes energy from the battery.

        :param energy: energy (in joules) to be taken from battery.
        """

        super().discharge(energy / 3600)

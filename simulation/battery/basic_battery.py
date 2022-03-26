import numpy as np
from numpy.polynomial import Polynomial

from simulation.battery.base_battery import BaseBattery


class BasicBattery(BaseBattery):
    """
    Class representing the DayBreak battery pack.

    Attributes:
        max_voltage (float): maximum voltage of the DayBreak battery pack (V)
        min_voltage (float): minimum voltage of the DayBreak battery pack (V)
        max_current_capacity (float): nominal capacity of the DayBreak battery pack (Ah)
        max_energy_capacity (float): nominal energy capacity of the DayBreak battery pack (Wh)

        state_of_charge (float): instantaneous battery state-of-charge (0.00 - 1.00)
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

        self.calculate_voltage_from_discharge_capacity = Polynomial([117.6, -0.858896])  # -0.8589x + 117.6

        self.calculate_energy_from_discharge_capacity = Polynomial([0, 117.6, -0.429448])  # -0.4294x^2 + 117.6x

        self.calculate_soc_from_discharge_capacity = Polynomial([1, -1 / self.max_current_capacity])

        self.calculate_discharge_capacity_from_soc = Polynomial([self.max_current_capacity, -self.max_current_capacity])

        self.calculate_discharge_capacity_from_energy = lambda x: 136.92 - np.sqrt(18747.06027 - 2.32857 * x)

        # ----- DayBreak battery variables -----

        self.state_of_charge = state_of_charge

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

        self.discharge_capacity = self.calculate_discharge_capacity_from_energy(energy_discharged)
        self.state_of_charge = self.calculate_soc_from_discharge_capacity(self.discharge_capacity)
        self.voltage = self.calculate_voltage_from_discharge_capacity(self.discharge_capacity)

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
        
        :return discharged_energy: energy (in joules) removed from the battery.
        """

        return super().discharge(energy / 3600)

    def update_array(self, cumulative_energy_array):
        """
        Performs energy calculations with NumPy arrays

        :param cumulative_energy_array: a NumPy array containing the cumulative energy changes at each time step
        experienced by the battery

        :return soc_array: a NumPy array containing the battery state of charge at each time step

        :return voltage_array: a NumPy array containing the voltage of the battery at each time step

        :return stored_energy_array: a NumPy array containing the energy stored in the battery at each time step
        step
        """

        stored_energy_array = np.full_like(cumulative_energy_array, fill_value=self.stored_energy)
        stored_energy_array += cumulative_energy_array / 3600
        stored_energy_array = np.clip(stored_energy_array, a_min=0, a_max=self.max_energy_capacity)

        energy_discharged_array = np.full_like(cumulative_energy_array, fill_value=self.max_energy_capacity) - \
                                  stored_energy_array

        discharge_capacity_array = self.calculate_discharge_capacity_from_energy(energy_discharged_array)

        soc_array = self.calculate_soc_from_discharge_capacity(discharge_capacity_array)
        voltage_array = self.calculate_voltage_from_discharge_capacity(discharge_capacity_array)

        return soc_array, voltage_array, stored_energy_array

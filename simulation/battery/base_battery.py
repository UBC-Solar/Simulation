from simulation.common import BatteryEmptyError
from simulation.common import Storage


class BaseBattery(Storage):
    def __init__(self, initial_energy, max_current_capacity, max_energy_capacity,
                 max_voltage, min_voltage, voltage, state_of_charge):
        super().__init__()

        # Constants
        self.max_current_capacity = max_current_capacity  # max capacity of battery (Ah)
        self.max_energy_capacity = max_energy_capacity  # max energy inside battery (Wh)

        self.max_voltage = max_voltage  # maximum battery voltage (V)
        self.min_voltage = min_voltage  # battery cut-off voltage (V)

        # Variables
        self.stored_energy = initial_energy  # energy inside battery (Wh)
        self.state_of_charge = state_of_charge  # battery state of charge
        self.voltage = voltage  # terminal voltage of the battery (V)

        if self.state_of_charge > 0:
            self.empty = False  # 1 if battery is empty, 0 if battery is not empty
        else:
            self.empty = True

    def update(self, tick):
        raise NotImplementedError

    def charge(self, energy):
        # handles the possibility that adding energy exceeds the max capacity of the battery
        if self.stored_energy + energy >= self.max_energy_capacity:
            self.stored_energy = self.max_energy_capacity
        else:
            self.stored_energy += energy

    def discharge(self, energy):
        # in the case that the required energy is more than what the battery currently stores
        if self.stored_energy - energy <= 0:
            # currently the remaining energy in the battery just evaporates but this should be changed in the future
            self.stored_energy = 0
            self.empty = True

            # TODO: consider removing exception
            raise BatteryEmptyError("ERROR: Battery is empty.\n")
        else:
            self.stored_energy -= energy
            return energy

    def is_empty(self):
        return self.empty

    def get_stored_energy(self):
        return self.stored_energy

    def get_state_of_charge(self):
        return self.state_of_charge

    def get_output_voltage(self):
        return self.voltage

    def __str__(self):
        return (f"Battery stored energy: {self.stored_energy:.2f}Wh\n"
                f"Battery state of charge: {self.state_of_charge * 100:.1f}%\n"
                f"Battery voltage: {self.voltage:.2f}V\n")

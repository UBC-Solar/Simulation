from abc import ABC, abstractmethod
from simulation.common import Storage


class BaseBattery(Storage):
    def __init__(self, initial_energy, max_current_capacity, max_energy_capacity,
                 max_voltage, min_voltage, voltage, state_of_charge):
        super().__init__()                                                       # calls Storage class __init__ method

        # Constants
        self.max_current_capacity = max_current_capacity                         # max capacity of battery (Ah)
        self.max_energy_capacity = max_energy_capacity                           # max energy inside battery (Wh)

        self.max_voltage = max_voltage                      # maximum battery voltage (V)
        self.min_voltage = min_voltage                      # battery cut-off voltage (V)

        # Variables
        self.stored_energy = initial_energy                             # energy inside battery (Wh)
        self.state_of_charge = state_of_charge                          # battery state of charge (%)
        self.depth_of_discharge = 1 - self.state_of_charge              # inverse of state of charge (%)
        self.voltage = voltage                                          # terminal voltage of the battery (V)

        if self.state_of_charge > 0:
            self.empty = 0                  # 1 if battery is empty, 0 if battery is not empty
        else:
            self.empty = 1

    def update(self, tick):             # not quite sure what to do with this function
        raise NotImplementedError       # probably updates all the attributes for a given time interval

    def charge(self, energy):
        if self.stored_energy + energy >= self.max_current_capacity:        # handles the possibility that adding energy exceeds the max capacity of the battery
            self.stored_energy = self.max_current_capacity
        else:
            self.stored_energy += energy

    def discharge(self, energy):                # removes energy from the battery and returns it as a number
        if self.stored_energy - energy <= 0:
            returned_energy = self.stored_energy
            self.stored_energy = 0
            self.empty = 1

            return returned_energy                  # i'm sure there's a cleaner way to do this
        else:
            self.stored_energy -= energy
            return energy

    def is_empty(self):
        return self.empty

    def __str__(self):
        return ("Battery stored energy: {}Wh".format(round(self.stored_energy, 2)) + "\n" + 
                "Battery state of charge: {}%".format(round(self.state_of_charge*100, 2)) + "\n" + 
                "Battery voltage: {}V \n".format(round(self.voltage, 2)))


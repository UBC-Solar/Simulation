from abc import ABC, abstractmethod
from simulation.common import Storage

class BaseBattery(Storage):
    def __init__(self, initial_energy, max_current_capacity, max_energy_capacity):
        super().__init__()                                                              # calls Storage class __init__ method

        # Class attributes
        self.stored_energy = initial_energy                                      # energy inside battery (Wh)
        self.max_current_capacity = max_current_capacity                         # max capacity of battery (Ah)
        self.max_energy_capacity = max_energy_capacity                           # max energy inside battery (Wh)

        self.state_of_charge = 1                                      # will be updated depending on changes in energy
        self.depth_of_discharge = 1 - self.state_of_charge
        self.voltage = 5                                              # terminal voltage of the battery
        self.max_voltage = 5
        self.min_voltage = 2.5

    def update(self, tick):             # not quite sure what to do with this function
        pass                            # probably updates all the attributes for a given time interval

    def charge(self, energy):
        if self.stored_energy + energy >= self.max_current_capacity:        # handles the possibility that adding energy exceeds the max capacity of the battery
            self.stored_energy = self.max_current_capacity
        else:
            self.stored_energy += energy

    def discharge(self, energy):                # this function removes the energy from the battery and returns it as a number
        if self.stored_energy - energy <= 0:
            returned_energy = self.stored_energy
            self.stored_energy = 0
            return returned_energy                  # i'm sure there's a cleaner way to do this
        else:
            self.stored_energy -= energy
            return energy

    def status_report(self):
        print("Battery stored energy: {}Wh".format(round(self.stored_energy, 2)))
        print("Battery state of charge: {}%".format(round(self.state_of_charge*100, 2)))
        print("Battery voltage: {}V \n".format(round(self.voltage, 2)))

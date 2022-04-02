from abc import ABC, abstractmethod


class Car(ABC):
    def __init__(self, array, battery, lvs, motor):
        self.array = array
        self.battery = battery
        self.lvs = lvs
        self.motor = motor

    def update(self, tick, array_energy, battery_energy, lvs_energy, motor_energy):
        delta_energy = array_energy + battery_energy + lvs_energy + motor_energy
        cumulative_delta_energy = np.cumsum(delta_energy)
        battery_variables_array = self.battery.update_array(cumulative_delta_energy)

from simulation.regen import BaseRegen
import numpy as np


class BasicRegen(BaseRegen):

    def __init__(self):
        super().__init__()
        self.efficiency = 0.5
        self.min_decel_mag = 0
        self.vehicle_mass = 250
        self.kmk_to_mps = 0.278

    def update():
        pass

    def calculate_produced_energy(self, tick, speed_kmh):
        """
        Returns a numpy array containing the energy produced by regen
        during each tick of the race based on the deceleration in that tick
        """

        acceleration = np.diff(speed_kmh, append=[0])
        deceleration_instances = np.where(acceleration < 0, np.abs(acceleration), np.zeros(len(acceleration)))

        self.produced_energy = self.calculate_change_energy(deceleration_instances)*self.efficiency

        return self.produced_energy

    def calculate_change_energy(self, speed_delta_kmh):
        """
        Calculate the change in kinetic energy caused by a change in speed
        :param speed_delta: an array containing the change in speeds
        """
        speed_delta_mps = self.kmk_to_mps*speed_delta_kmh

        return 0.5*self.vehicle_mass*speed_delta_mps**2

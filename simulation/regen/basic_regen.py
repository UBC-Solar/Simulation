from simulation.regen import BaseRegen
import numpy as np


class BasicRegen(BaseRegen):
    GRAVITY = 9.81
    EFFICIENCY = 0.5  # currently set to 50% but best case scenario is 60-70%

    def __init__(self):
        super().__init__()
        self.min_decel_mag = 0
        self.vehicle_mass = 250
        self.kmh_to_mps = 0.278

    def update():
        pass

    def calculate_produced_energy(self, speed_kmh, gis_route_elevations):
        """
        Returns a numpy array containing the energy produced by regen
        during each tick of the race based on the change in energy in that tick
        :param speed_kmh: an array containing the speeds at each tick
        :param gis_route_elevations: an array containing elevations on the route at each tick
        """

        # get the changes of energy from tick i to tick i + 1
        delta_kinetic_energy = np.diff((1 / 2) * self.vehicle_mass * pow(speed_kmh, 2), append=[0])
        delta_potential_energy = np.diff(self.vehicle_mass * self.GRAVITY * gis_route_elevations, append=[0])

        # get the total change in energy at each tick
        delta_energy = delta_kinetic_energy + delta_potential_energy

        # create regen energy produced array
        # if delta_energy is negative, we regen that energy back at the set efficiency rate; else 0 energy regen
        self.produced_energy = np.where(delta_energy < 0, abs(delta_energy) * self.EFFICIENCY, 0)

        return self.produced_energy


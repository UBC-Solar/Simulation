from simulation.model.car.regen import BaseRegen
import numpy as np
from simulation.common import BrightSide


class BasicRegen(BaseRegen):
    GRAVITY = 9.81
    EFFICIENCY = 0.5  # currently set to 50% but best case scenario is 60-70%

    def __init__(self):
        super().__init__()
        self.min_decel_mag = 0
        self.vehicle_mass = BrightSide.vehicle_mass
        self.kmh_to_mps = 0.278

    def calculate_produced_energy(self, speed_kmh, gis_route_elevations, parameters=None):
        """
        Returns a numpy array containing the energy produced by regen
        during each tick of the race based on the change in energy in that tick
        :param speed_kmh: an array containing the speeds at each tick
        :param gis_route_elevations: an array containing elevations on the route at each tick
        """
        if parameters is None:
            parameters = self.parameters

        # get the changes of energy from tick i to tick i + 1
        speed_ms = speed_kmh / 3.6  # Convert to m/s from km/h
        delta_kinetic_energy = np.diff((1 / 2) * self.vehicle_mass * pow(speed_ms, 2), append=[0])
        delta_potential_energy = np.diff(self.vehicle_mass * self.GRAVITY * gis_route_elevations, append=[0])

        # get the total change in energy at each tick
        delta_energy = delta_kinetic_energy + delta_potential_energy

        # create regen energy produced array
        # if delta_energy is negative, we regen that energy back at the set efficiency rate; else 0 energy regen
        self.produced_energy = np.where(delta_energy < 0, abs(delta_energy) * self.EFFICIENCY, 0)

        # Regen does not occur below a certain speed
        self.produced_energy = np.where(speed_ms >= parameters[0], self.produced_energy, 0)

        # Regen power is capped by current limitations
        self.produced_energy = np.clip(self.produced_energy, a_min=0, a_max=parameters[1])

        # Perform scaling for fitting to data
        self.produced_energy *= np.polyval([parameters[2], parameters[3]], self.produced_energy)

        return self.produced_energy


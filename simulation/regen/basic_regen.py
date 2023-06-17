from simulation.regen.base_regen import BaseRegen
import numpy as np


class BasicRegen(BaseRegen):
    def __init__(self):
        super().__init__()

    def update(self, tick, speed_kmh):
        acceleration = np.diff(speed_kmh)

        deceleration_instances = np.where(acceleration < 0, acceleration, np.zeros(len(acceleration)))
        print(deceleration_instances)

        self.produced_energy = 0
        return self.produced_energy * tick

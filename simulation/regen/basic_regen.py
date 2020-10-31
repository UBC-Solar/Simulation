from simulation.regen.base_regen import BaseRegen


class BasicRegen(BaseRegen):
    def __init__(self):
        super().__init__()

    def update(self, tick):
        self.produced_energy = 0
        return self.produced_energy * tick

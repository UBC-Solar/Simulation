from simulation.lvs.base_lvs import BaseLVS


class BasicLVS(BaseLVS):

    def __init__(self, consumed_energy):
        super().__init__(consumed_energy)

    def update(self, tick):
        pass

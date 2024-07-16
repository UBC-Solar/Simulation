from simulation.common.component import Component


class Storage(Component):
    """

    The base storage model

    :param float stored_energy: amount of energy stored in the storage module

    """

    def __init__(self, stored_energy=0):
        super().__init__()
        self.stored_energy = stored_energy


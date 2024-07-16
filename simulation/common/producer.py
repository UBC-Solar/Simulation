from simulation.common.component import Component


class Producer(Component):
    """

    The base producer model

    :param float produced_energy: the initial state for produced energy

    """

    def __init__(self, produced_energy=0):
        super().__init__()
        self.produced_energy = produced_energy


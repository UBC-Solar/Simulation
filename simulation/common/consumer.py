from simulation.common.component import Component
from simulation.config.parameters import get_parameters


class Consumer(Component):
    """

    The base consumer model

    :param consumed_energy: (float) the initial state for consumed energy

    """

    def __init__(self, consumed_energy):
        super().__init__()
        self.consumed_energy = consumed_energy

    def get_consumed_energy(self):
        return self.consumed_energy


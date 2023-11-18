from abc import ABC, abstractmethod


class Consumer(ABC):
    """

    The base consumer model

    :param consumed_energy: (float) the initial state for consumed energy

    """

    def __init__(self, consumed_energy):
        self.consumed_energy = consumed_energy

    def get_consumed_energy(self):
        return self.consumed_energy

    def set_consumed_energy(self, value):
        self.consumed_energy = value

    def update_consumed_energy(self):
        energy = self.get_consumed_energy()
        self.set_consumed_energy(0)
        return energy

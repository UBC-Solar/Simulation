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


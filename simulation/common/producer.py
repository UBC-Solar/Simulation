from abc import ABC, abstractmethod


class Producer(ABC):
    """

    The base producer model

    :param float produced_energy: the initial state for produced energy

    """

    def __init__(self, produced_energy=0):
        self.produced_energy = produced_energy

    @abstractmethod
    def update(self, tick):
        """

        Updates model for a single tick

        :param float tick: the length of time for the tick (in seconds)

        """

        raise NotImplementedError

    def get_produced_energy(self):
        return self.produced_energy

    def set_produced_energy(self, value):
        self.produced_energy = value

    def update_produced_energy(self):
        energy = self.get_produced_energy()
        self.set_produced_energy(0)
        return energy

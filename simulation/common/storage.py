from abc import ABC, abstractmethod


class Storage(ABC):
    """

    The base storage model

    :param float stored_energy: amount of energy stored in the storage module

    """

    def __init__(self, stored_energy=0):
        self.stored_energy = stored_energy

    @abstractmethod
    def update(self, tick):
        raise NotImplementedError

    @abstractmethod
    def charge(self, energy):
        raise NotImplementedError

    @abstractmethod
    def discharge(self, energy):
        raise NotImplementedError

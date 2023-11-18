from abc import ABC, abstractmethod


class Producer(ABC):
    """

    The base producer model

    :param float produced_energy: the initial state for produced energy

    """

    def __init__(self, produced_energy=0):
        self.produced_energy = produced_energy


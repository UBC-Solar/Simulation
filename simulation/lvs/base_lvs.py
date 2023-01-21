from abc import ABC, abstractmethod
from Simulation.simulation.common import Consumer


class BaseLVS(Consumer):
    def __init__(self, consumed_energy):
        super().__init__(consumed_energy)

from abc import ABC, abstractmethod
from simulation.common import Consumer

class BaseLVS(Consumer):
    def __init__(self):
        super().__init__(self)
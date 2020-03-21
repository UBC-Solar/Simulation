from abc import ABC, abstractmethod
from simulation.common import Consumer

class BaseMotor(Consumer):
    def __init__(self):
        super().__init__(self)
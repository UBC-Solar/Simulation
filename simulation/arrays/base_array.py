from abc import ABC, abstractmethod
from simulation.common import Producer


class BaseArray(Producer):
    def __init__(self):
        super().__init__()
        # do array initialization

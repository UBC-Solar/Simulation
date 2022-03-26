from abc import abstractmethod
from simulation.utils.InputBounds import InputBounds


class BaseOptimization:
    def __init__(self, bounds: InputBounds, f):
        self.bounds = bounds
        self.func = f
        self.result = None
        self.target = float('-inf')
        self.bestinput = []

    @abstractmethod
    def maximize(self):
        raise NotImplementedError()

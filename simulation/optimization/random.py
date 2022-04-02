import random
from simulation.optimization.base_optimization import BaseOptimization
from simulation.utils.InputBounds import InputBounds


class RandomOptimization(BaseOptimization):
    def __init__(self, bounds: InputBounds, f):
        BaseOptimization.__init__(self, bounds, f)

    def maximize(self, iterations=10):
        best = float('-inf')
        bound_dict = self.bounds.get_bound_dict()
        for _ in range(iterations):
            inputs = {item[0]: random.uniform(item[1][0], item[1][1]) for item in bound_dict.items()}
            result = self.func(**inputs)
            if result > best:
                best = result
                self.bestinput = list(inputs.values())

        self.target = best
        return self.bestinput

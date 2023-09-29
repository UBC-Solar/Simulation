import bayes_opt
from simulation.optimization.base_optimization import BaseOptimization
from simulation.utils.InputBounds import InputBounds


class BayesianOptimization(BaseOptimization):
    def __init__(self, bounds: InputBounds, f):
        BaseOptimization.__init__(self, bounds, f)
        self.optimizer = bayes_opt.BayesianOptimization(self.func, self.bounds.get_bound_dict(), verbose=2)

    def maximize(self, init_points=5, n_iter=25, acq="ucb", kappa=10):
        acquisition_function = bayes_opt.util.UtilityFunction(kind=acq, kappa=kappa)
        self.optimizer.maximize(init_points=init_points, n_iter=n_iter, acquisition_function=acquisition_function)
        self.result = self.optimizer.max
        self.bestinput = list(self.result["params"].values())
        self.target = self.result["target"]
        return self.bestinput

import numpy as np
import pygad
from simulation.main import Simulation
from simulation.utils import InputBounds
from simulation.optimization.base_optimization import BaseOptimization
from simulation.common.helpers import denormalize, cull_dataset, linearly_transform, normalize


class GeneticOptimization(BaseOptimization):
    def __init__(self, model: Simulation, bounds: InputBounds, input_speed: np.ndarray):
        super().__init__(bounds, model.run_model)
        self.model = model
        self.bounds = bounds.get_bounds_list()

        fitness_function = self.fitness

        num_generations = 1
        num_parents_mating = 4

        sol_per_pop = 4
        num_genes = int(bounds[0])

        init_range_low = 0
        init_range_high = 1

        parent_selection_type = "sss"
        keep_parents = 1

        crossover_type = "single_point"

        mutation_type = "random"
        mutation_percent_genes = 10

        self.ga_instance = pygad.GA(num_generations=num_generations,
                                    num_parents_mating=num_parents_mating,
                                    fitness_func=fitness_function,
                                    sol_per_pop=sol_per_pop,
                                    num_genes=num_genes,
                                    init_range_low=init_range_low,
                                    init_range_high=init_range_high,
                                    parent_selection_type=parent_selection_type,
                                    keep_parents=keep_parents,
                                    crossover_type=crossover_type,
                                    mutation_type=mutation_type,
                                    mutation_percent_genes=mutation_percent_genes)

    def fitness(self, ga_instance, solution, solution_idx):
        solution_denormalized = denormalize(solution, self.bounds[2], self.bounds[1])
        results = self.func(solution_denormalized)
        fitness = results if self.model.was_successful() else self.model.get_distance_before_exhaustion()
        print(f"Fitness is {fitness}, results were {results}.")
        return fitness

    def maximize(self):
        self.ga_instance.run()
        return self.output()

    def output(self):
        solution, solution_fitness, solution_idx = self.ga_instance.best_solution()
        self.bestinput = denormalize(solution, self.bounds[2], self.bounds[1])
        print("Parameters of the best solution : {solution}".format(solution=self.bestinput))
        print("Fitness value of the best solution = {solution_fitness}".format(solution_fitness=solution_fitness))
        self.plot_fitness()
        return self.bestinput

    def plot_fitness(self):
        self.ga_instance.plot_fitness(save_dir="")

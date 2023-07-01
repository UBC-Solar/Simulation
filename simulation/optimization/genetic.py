import os
import pygad
import numpy as np

from simulation.main import Simulation
from simulation.utils import InputBounds
from simulation.optimization.base_optimization import BaseOptimization
from simulation.common.helpers import denormalize, cull_dataset, linearly_transform, normalize
from simulation.cache.optimization_population import population_directory


class GeneticOptimization(BaseOptimization):
    def __init__(self, model: Simulation, bounds: InputBounds, input_speed: np.ndarray):
        super().__init__(bounds, model.run_model)
        self.model = model
        self.bounds = bounds.get_bounds_list()

        fitness_function = self.fitness

        num_generations = 20
        num_parents_mating = 4

        sol_per_pop = 2

        parent_selection_type = "tournament"
        K_tournament = 4
        keep_elitism = 2

        crossover_type = "scattered"

        mutation_type = "random"
        mutation_percent_genes = 25

        gene_space = {'low': 0.0, 'high': 1.0}
        delay_after_generation = 0.0
        mutation_max_value = 0.1

        initial_population = self.get_initial_population(input_speed, sol_per_pop)

        self.ga_instance = pygad.GA(num_generations=num_generations,
                                    initial_population=initial_population,
                                    num_parents_mating=num_parents_mating,
                                    fitness_func=fitness_function,
                                    parent_selection_type=parent_selection_type,
                                    K_tournament=K_tournament,
                                    keep_elitism=keep_elitism,
                                    crossover_type=crossover_type,
                                    mutation_type=mutation_type,
                                    mutation_percent_genes=mutation_percent_genes,
                                    gene_space=gene_space,
                                    on_generation=lambda x: print("New generation!"),
                                    delay_after_gen=delay_after_generation,
                                    random_mutation_max_val=mutation_max_value)

    def get_initial_population(self, input_speed, num_arrays_to_generate):
        population_file = population_directory / "initial_population.npz"

        if os.path.isfile(population_file):
            with np.load(population_file) as population_data:
                if population_data['hash_key'] == self.model.hash_key:
                    print("Found cached initial population!")
                    initial_population = np.array(population_data['population'])
                    return initial_population
                else:
                    print("Hash key did not match, generating new initial population!")
        else:
            print("Did not find cached initial population, generating new initial population!")

        new_initial_population = self.generate_valid_speed_arrays(input_speed, num_arrays_to_generate)

        with open(population_file, 'wb') as f:
            print("Caching new population!")
            np.savez(f, hash_key=self.model.hash_key, population=new_initial_population)

        return new_initial_population

    def generate_valid_speed_arrays(self, input_speed, num_arrays_to_generate):
        if not self.model.check_if_has_calculated(raiseException=False):
            self.model.run_model(speed=input_speed, plot_results=True)
        SOC = self.model.get_results(["state_of_charge"])
        speed_arrays = []

        while len(speed_arrays) < num_arrays_to_generate:
            culled_SOC = cull_dataset(SOC, int(len(SOC) / len(input_speed)))
            guess_speed = input_speed * linearly_transform(culled_SOC, 1.5, 0.50)[0:len(input_speed)]
            guess_speed = linearly_transform(guess_speed, 50, 30)
            self.model.run_model(speed=guess_speed, plot_results=True)
            SOC = self.model.get_results(["state_of_charge"])
            if self.model.was_successful():
                speed_arrays.append(normalize(guess_speed))
            input_speed = guess_speed

        return speed_arrays

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

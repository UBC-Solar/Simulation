import os
import pygad
import numpy as np

from simulation.main import Simulation
from simulation.utils import InputBounds
from simulation.optimization.base_optimization import BaseOptimization
from simulation.common.helpers import denormalize, cull_dataset, rescale, normalize, linearly_interpolate
from simulation.cache.optimization_population import population_directory
from simulation.data.results import results_directory


"""

See the following resources for explanations of genetic algorithms and different hyperparameters:
1. start here:
    https://blog.derlin.ch/genetic-algorithms-with-pygad 
2. pygad:
    https://pygad.readthedocs.io/en/latest/pygad.html
3. genetic algorithm:
    https://towardsdatascience.com/introduction-to-optimization-with-genetic-algorithm-2f5001d9964b
4. parent selection:
    https://en.wikipedia.org/wiki/Selection_(genetic_algorithm)
5. crossover types:
    https://en.wikipedia.org/wiki/Crossover_(genetic_algorithm)
    
"""


class GeneticOptimization(BaseOptimization):
    def __init__(self, model: Simulation, bounds: InputBounds, input_speed: np.ndarray):
        super().__init__(bounds, model.run_model)
        self.model = model
        self.bounds = bounds.get_bounds_list()

        fitness_function = self.fitness

        # Define how many iterations that GA will run
        num_generations = 30

        # Define how many parents will be used for the creation of offspring for each subsequent generation
        num_parents_mating = 4

        # Define the size of the population (number of chromosomes)
        # More chromosomes means a larger gene pool (should result in superior optimization) but at the cost of
        # needing to calculate the fitness of more chromosomes.
        self.sol_per_pop = 12

        # Define how parents are selected from the population
        # 'tournament' will result in tournament selection, 'sss' for steady-state selection,
        parent_selection_type = "tournament"

        # Define number of chromosomes in each tournament
        K_tournament = 4

        # Define the number of the best chromosomes that will be kept in the next generation
        keep_elitism = 3

        # Define the type of crossover that will be used in offspring creation
        # 'single_point' for single-point crossover, 'two_points' for double-point, 'scattered' for scattered crossover
        # and 'uniform' for uniform crossover.
        crossover_type = "two_points"

        # Define the type of mutation that will be used in offspring creation
        mutation_type = "random"

        # Define the number of genes that will be mutated (0 <= x < 1)
        mutation_percent_genes = 25

        # Define a maximum value for gene value mutations (should be 0 < x < 1)
        mutation_max_value = 0.1

        # Bound the value of each gene to be between 0 and 1 as chromosomes should be normalized.
        gene_space = {'low': 0.0, 'high': 1.0}

        # Add a time delay between generations (used for debug purposes)
        delay_after_generation = 0.0

        initial_population = self.get_initial_population(input_speed, self.sol_per_pop)

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

    def get_initial_population(self, input_speed, num_arrays_to_generate, force_new_generation=True):
        population_file = population_directory / "initial_population.npz"

        if os.path.isfile(population_file) and not force_new_generation:
            with np.load(population_file) as population_data:
                if population_data['hash_key'] == self.model.hash_key:
                    print("Found cached initial population!")
                    initial_population = np.array(population_data['population'])
                    if len(initial_population) == self.sol_per_pop:
                        return initial_population
                    else:
                        print("Cached population size does not match, generating new initial population! ")
                else:
                    print("Hash key did not match, generating new initial population!")
        else:
            print("Generating new initial population!")

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
            guess_speed = input_speed * rescale(culled_SOC, 1.5, 0.50)[0:len(input_speed)]
            guess_speed = rescale(guess_speed, 50, 30)
            # guess_speed = linearly_interpolate(input_speed, guess_speed, 0.5)
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
        register_file = results_directory / "register.npz"
        x = None

        with np.load(register_file) as population_data:
            x = population_data['x']
            x += 1
            np.savez(register_file, x=x)

        graph_title = "sequence" + str(x)
        save_dir = results_directory / graph_title
        self.ga_instance.plot_fitness(title=graph_title, save_dir=save_dir)


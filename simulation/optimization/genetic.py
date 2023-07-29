import os
import pygad
import numpy as np
from strenum import StrEnum
import csv

from simulation.main import Simulation
from simulation.utils import InputBounds
from simulation.optimization.base_optimization import BaseOptimization
from simulation.common.helpers import denormalize, cull_dataset, rescale, normalize
from simulation.cache.optimization_population import population_directory
from simulation.data.results import results_directory
from tqdm import tqdm

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


class Parent_Selection_Type(StrEnum):
    sss = "sss"
    tournament = "tournament"
    stochastic = "stochastic"
    rank = "rank"


class Mutation_Type(StrEnum):
    random = "random"


class Crossover_Type(StrEnum):
    single_point = "single_point"
    two_points = "two_points"
    scattered = "scattered"
    uniform = "uniform"


class OptimizationSettings:
    def __init__(self, chromosome_size=4,
                 parent_selection_type=Parent_Selection_Type.sss,
                 generation_limit=1,
                 num_parents=4,
                 k_tournament=4,
                 crossover_type=Crossover_Type.two_points,
                 elitism=3,
                 mutation_type=Mutation_Type.random,
                 mutation_percent=25.0,
                 max_mutation=0.05):
        self.chromosome_size: int = chromosome_size
        self.parent_selection_type: Parent_Selection_Type = parent_selection_type
        self.generation_limit: int = generation_limit
        self.num_parents: int = num_parents
        self.k_tournament: int = k_tournament
        self.crossover_type: Crossover_Type = crossover_type
        self.elitism: int = elitism
        self.mutation_type: Mutation_Type = mutation_type
        self.mutation_percent: float = mutation_percent
        self.max_mutation: float = max_mutation

        self._fitness: float = 0

    def as_list(self):
        out_list: list = [str(self.chromosome_size), str(self.parent_selection_type), str(self.generation_limit),
                          str(self.num_parents), str(self.k_tournament), str(self.crossover_type),str(self.elitism),
                          str(self.mutation_type), str(self.mutation_percent), str(self.max_mutation),
                          str(self._fitness)]
        return out_list

    def set_fitness(self, fitness):
        self._fitness = fitness


class GeneticOptimization(BaseOptimization):

    def __init__(self, model: Simulation, bounds: InputBounds, input_speed: np.ndarray,
                 force_new_population_flag: bool = False, settings: OptimizationSettings = None, pbar: tqdm = None):
        super().__init__(bounds, model.run_model)
        self.model = model
        self.bounds = bounds.get_bounds_list()
        fitness_function = self.fitness
        self.settings = settings if settings is not None else OptimizationSettings()
        self.pbar = pbar if pbar is not None else tqdm()

        # Define how many iterations that GA will run
        num_generations = self.settings.generation_limit

        # Define how many parents will be used for the creation of offspring for each subsequent generation
        num_parents_mating = self.settings.num_parents

        # Define the size of the population (number of chromosomes)
        # More chromosomes means a larger gene pool (should result in superior optimization) but at the cost of
        # needing to calculate the fitness of more chromosomes.
        self.sol_per_pop = self.settings.chromosome_size

        # Define how parents are selected from the population
        # 'tournament' will result in tournament selection, 'sss' for steady-state selection,
        parent_selection_type = self.settings.parent_selection_type

        # Define number of chromosomes in each tournament
        K_tournament = self.settings.k_tournament

        # Define the number of the best chromosomes that will be kept in the next generation
        keep_elitism = self.settings.elitism

        # Define the type of crossover that will be used in offspring creation
        # 'single_point' for single-point crossover, 'two_points' for double-point, 'scattered' for scattered crossover
        # and 'uniform' for uniform crossover.
        crossover_type = self.settings.crossover_type

        # Define the type of mutation that will be used in offspring creation
        mutation_type = self.settings.mutation_type

        # Define the number of genes that will be mutated (0 <= x < 1)
        mutation_percent_genes = self.settings.mutation_percent

        # Define a maximum value for gene value mutations (should be 0 < x < 1)
        mutation_max_value = self.settings.max_mutation

        # Bound the value of each gene to be between 0 and 1 as chromosomes should be normalized.
        gene_space = {'low': 0.0, 'high': 1.0}

        # Add a time delay between generations (used for debug purposes)
        delay_after_generation = 0.0

        # We must obtain or create an initial population for GA to work with.
        initial_population = self.get_initial_population(input_speed, self.sol_per_pop, force_new_population_flag)

        # This informs GA when to end the optimization sequence. If blank, it will continue until the generation
        # iterations finish. Write "saturate_x" for the sequence to end after x generations of no improvement to
        # fitness. Write "reach_x" for the sequence to end after fitness has reached x.
        stop_criteria = "saturate_10"

        self.ga_instance = pygad.GA(num_generations=num_generations,
                                    initial_population=initial_population,
                                    num_parents_mating=num_parents_mating,
                                    fitness_func=fitness_function,
                                    parent_selection_type=str(parent_selection_type),
                                    K_tournament=K_tournament,
                                    keep_elitism=keep_elitism,
                                    crossover_type=str(crossover_type),
                                    mutation_type=str(mutation_type),
                                    mutation_percent_genes=mutation_percent_genes,
                                    gene_space=gene_space,
                                    on_generation=lambda x: pbar.update(1),
                                    delay_after_gen=delay_after_generation,
                                    random_mutation_max_val=mutation_max_value,
                                    stop_criteria=stop_criteria)

    def get_initial_population(self, input_speed, num_arrays_to_generate, force_new_population_flag):
        population_file = population_directory / "initial_population.npz"

        if os.path.isfile(population_file) and not force_new_population_flag:
            with np.load(population_file) as population_data:
                if population_data['hash_key'] == self.model.hash_key:
                    initial_population = np.array(population_data['population'])
                    if len(initial_population) == self.sol_per_pop:
                        print("\nPrevious initial population save file is being used...")
                        return initial_population

        new_initial_population = self.generate_valid_speed_arrays(input_speed, num_arrays_to_generate)

        with open(population_file, 'wb') as f:
            np.savez(f, hash_key=self.model.hash_key, population=new_initial_population)

        return new_initial_population

    def generate_valid_speed_arrays(self, input_speed, num_arrays_to_generate):
        max_speed_kmh = 50
        min_speed_kmh = 30
        upper_stretch_bound = 1.5
        lower_stretch_bound = 0.5

        if not self.model.check_if_has_calculated(raiseException=False):
            self.model.run_model(speed=input_speed, plot_results=False)
        SOC = self.model.get_results(["raw_soc"])
        speed_arrays = []

        while len(speed_arrays) < num_arrays_to_generate:
            # We will sample SOC at as many points as the speed array needs
            culled_SOC = cull_dataset(SOC, int(len(SOC) / len(input_speed)))[0:len(input_speed)]
            # Rescale SOC to obtain a "coefficient" for each speed that should roughly
            # match whether the car should speed up or slow down given the SOC at that time
            speed_coefficients = rescale(culled_SOC, upper_stretch_bound, lower_stretch_bound)
            # Multiply input speed by coefficients and finally rescale the result
            guess_speed = rescale(speed_coefficients * input_speed, max_speed_kmh, min_speed_kmh)

            self.model.run_model(speed=guess_speed, plot_results=True)
            SOC = self.model.get_results(["raw_soc"])
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
        self.settings.set_fitness(solution_fitness)
        return self.bestinput

    def plot_fitness(self):
        sequence_index = GeneticOptimization.get_sequence_index()

        graph_title = "sequence" + str(sequence_index)
        save_dir = results_directory / graph_title

        self.ga_instance.plot_fitness(title=graph_title, save_dir=save_dir)

    def write_results(self):
        results_file = results_directory / "results.csv"
        with open(results_file, 'a') as f:
            writer = csv.writer(f)
            sequence_index: str = str(GeneticOptimization.get_sequence_index(increment_index=False))
            output = list(self.settings.as_list())
            output.insert(0, sequence_index)
            print("Writing: " + str(output))
            writer.writerow(output)

    @staticmethod
    def get_sequence_index(increment_index=True):
        register_file = results_directory / "register.npz"

        if not os.path.isfile(register_file):
            np.savez(register_file, x=0)
            return 0

        with np.load(register_file) as register_data:
            x = register_data['x']
            x += 1
            if increment_index:
                np.savez(register_file, x=x)
            return x


def reset_register():
    register_file = results_directory / "register.npz"

    if not os.path.isfile(register_file):
        np.savez(register_file, x=0)

    with np.load(register_file):
        np.savez(register_file, x=0)


def parse_csv_into_settings(csv_reader: csv.reader) -> list:
    settings_list = []

    for row in csv_reader:
        chromosome_size = int(row[0])
        parent_selection_type = Parent_Selection_Type(row[1])
        generations_limit = int(row[2])
        num_parents = int(row[3])
        k_tournament = int(row[4])
        crossover_type = Crossover_Type(row[5])
        elitism = int(row[6])
        mutation_type = Mutation_Type(row[7])
        mutation_percent = float(row[8])
        max_mutation = float(row[9])
        new_setting = OptimizationSettings(chromosome_size, parent_selection_type, generations_limit, num_parents,
                                           k_tournament, crossover_type, elitism, mutation_type, mutation_percent,
                                           max_mutation)
        settings_list.append(new_setting)

    return settings_list


if __name__ == "__main__":
    reset_register()
    print(GeneticOptimization.get_sequence_index(increment_index=False))

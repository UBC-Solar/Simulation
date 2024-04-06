import numpy as np
import zipfile
import pygad
import json
import math
import sys
import csv
import os

from strenum import StrEnum
from tqdm import tqdm

from simulation.cache.optimization_population import population_directory
from simulation.optimization.base_optimization import BaseOptimization
from simulation.common.helpers import denormalize, normalize, rescale
from simulation.data.results import results_directory
from simulation.common.noise import Noise
from simulation.utils import InputBounds
from simulation.main import Simulation, SimulationReturnType

"""

Genetic Optimization (also known as Genetic Algorithm, or GA) follows the following primary steps:

Fitness Evaluation -> Parent Selection -> Offspring Creation -> Repeat

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
    
Notable Vocabulary:

1. Chromosome: a chromosome is a set of genes that describe a potential solution. In the context of UBC Solar's 
Simulation where we are optimizing driving speeds, a chromosome is a driving speeds array.

2. Gene: a gene is an element of a chromosome and genes are what will be modified through the course of optimization.
In our context where a chromosome is an abstraction of a driving speeds array, a gene represents the value for
a single driving speed interval. 

3. Generation: a generation can be thought of as a single iteration of the optimization sequence. The members of a 
generation will be evaluated, parents selected from, and then mated to create offspring. Depending on hyperparameters,
some chromosomes from a given generation may proceed to be a member of the following generation.

3. Population: the set of chromosomes that exist within a generation, a generation's population is 
the possible solutions that are "participating" in the optimization process during a given generation. 
To begin the optimization process, we create an initial population of guess solutions as a launching point.

5. Offspring: the resulting chromosome from crossover and mutation of parents that have been selected following
fitness evaluation. Usually, all offspring proceed to the next generation where they will then be evaluated, and 
process continues.

6. Convergence: in the context of GA, convergence is how quickly GA arrives at a maximum (local or global) fitness 
value. On a Fitness vs Generation graph, convergence is the rate in which fitness plateaus. 

7. "Successful Simulation": in its current state, Simulation can simulate a driving speeds array that 
results in state of charge dropping below 0%, which is a physical impossibility. A successful simulation is 
one where this does not occur, and a successful/valid driving speeds array is one that will result in a successful
simulation.

"""


class OptimizationSettings:
    """

    This class is a container for the hyperparameters of GA.
    See the resources listed above for a description of each hyperparameter, they are also described
    in the constructor of GA.
    The default parameters of this class's constructor define the default hyperparameters of GA.
    This class also contains enums to discretize applicable, non-numeric hyperparameters.

    Note: certain hyperparameters will override or modify the behaviour of others, see
    https://pygad.readthedocs.io/en/latest/pygad.html for detailed descriptions.

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

    class Stopping_Criteria:
        class Criteria_Type(StrEnum):
            saturate = "saturate"
            reach = "reach"

        def __init__(self, criteria: Criteria_Type = Criteria_Type.saturate, value: int = 10, string: str = None):
            self.string = string
            self.criteria = criteria
            self.value = value

        def __str__(self):
            if self.string is not None:
                return self.string
            return str(self.criteria) + "_" + str(self.value)

        saturate: Criteria_Type = Criteria_Type.saturate
        reach: Criteria_Type = Criteria_Type.reach

    def __init__(self, chromosome_size: int = 24,
                 parent_selection_type: Parent_Selection_Type = Parent_Selection_Type.tournament,
                 generation_limit: int = 30,
                 num_parents: int = 12,
                 k_tournament: int = 5,
                 crossover_type: Crossover_Type = Crossover_Type.single_point,
                 elitism: int = 8,
                 mutation_type: Mutation_Type = Mutation_Type.random,
                 mutation_percent: float = 25.0,
                 max_mutation: float = 0.05,
                 stopping_criteria: Stopping_Criteria = Stopping_Criteria(Stopping_Criteria.saturate, 15)):
        self.chromosome_size: int = chromosome_size
        self.parent_selection_type: OptimizationSettings.Parent_Selection_Type = parent_selection_type
        self.generation_limit: int = generation_limit
        self.num_parents: int = num_parents
        self.k_tournament: int = k_tournament
        self.crossover_type: OptimizationSettings.Crossover_Type = crossover_type
        self.elitism: int = elitism
        self.mutation_type: OptimizationSettings.Mutation_Type = mutation_type
        self.mutation_percent: float = mutation_percent
        self.max_mutation: float = max_mutation
        self.stopping_criteria: OptimizationSettings.Stopping_Criteria = stopping_criteria

        self._fitness: float = 0

    def as_list(self) -> list[str]:
        """

        Returns all optimization settings and the stored, associated fitness value as a list that
        can be outputted as a row to a CSV spreadsheet.

        :return: a list containing each hyperparameter as a string

        """

        out_list: list[str] = [str(self.chromosome_size), str(self.parent_selection_type), str(self.generation_limit),
                               str(self.num_parents), str(self.k_tournament), str(self.crossover_type),
                               str(self.elitism), str(self.mutation_type), str(self.mutation_percent),
                               str(self.max_mutation), str(self.stopping_criteria), str(self._fitness)]
        return out_list

    def set_fitness(self, fitness: float) -> None:
        """

        Set the fitness value of this hyperparameter configuration.

        :param float fitness: the fitness achieved by this configuration

        """

        self._fitness = fitness


class GeneticOptimization(BaseOptimization):
    """

    GeneticOptimization uses the PyGAD module to implement a genetic algorithm-based optimization sequence.

    Briefly, GA begins by evaluating an initial population, selecting certain potential solutions (chromosomes) to be
    parents, creating offspring solutions from the parents, and repeating for a certain number of generations or
    until a stopping condition is met.

    To learn how GA works, read the resources enumerated at the top of this file (`genetic.py`).

    To modify GA's default hyperparameters, modify the default parameters of OptimizationSettings' constructor.

    To evaluate different hyperparameter configurations, use the "run_hyperparameter_search"
    method in `run_simulation.py`. To view already evaluated hyperparameters, view the "Hyperparameter Search"
    folder in UBC Solar's Software Google Drive.

    """

    def __init__(self, model: Simulation, bounds: InputBounds, force_new_population_flag: bool = False,
                 settings: OptimizationSettings = None, pbar: tqdm = None, plot_fitness: bool = False):

        assert model.return_type is SimulationReturnType.distance_and_time, \
            "Simulation Model for Genetic Optimization must have return type: SimulationReturnType.distance_and_time!"

        super().__init__(bounds, model.run_model)
        self.model = model
        self.bounds = bounds.get_bounds_list()
        self.settings = settings if settings is not None else OptimizationSettings()
        self.output_hyperparameters = plot_fitness
        self.did_finish_race = None

        # Define the function that will be used to determine the fitness of each chromosome
        fitness_function = self.fitness

        # https://www.desmos.com/calculator/gvknyspywa
        def sigmoid(a, c, race_length):
            return lambda x: 1 / (1 + math.exp(-(a * x + (-(math.log(1 / c - 1) + a * race_length)))))

        # https://www.desmos.com/calculator/uncbg8hnvq
        def amplifier(race_length):
            return lambda x: math.pow(math.sqrt(3) * (race_length - x) / (-x), 2) + 1

        # coefficients 0.085 and 0.985 are numbers chosen to generate the function curve desired: see the Desmos graph
        self.fitness_sigmoid = sigmoid(0.03, 0.985, self.model.get_race_length() / 1000.0)
        self.fitness_amplifier = amplifier(self.model.simulation_duration)

        # Define how many generations that GA will run (sequence may end prematurely depending on
        # if a stopping condition has been defined!)
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
        # Importantly, GA generates as many offspring as it needs to complete the population of the subsequent
        # generation, meaning more parents being kept means less offspring will be created.
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

        # Bind the value of each gene to be between 0 and 1 as chromosomes should be normalized.
        gene_space = {'low': 0.0, 'high': 1.0}

        # Add a time delay between generations (used for debug purposes)
        delay_after_generation = 0.0

        # Store diversity of generation per optimization iteration
        self.diversity = []

        # Define a function to be run when a generation begins
        def on_generation_callback(x):
            """
            Callback function that is called after each generation/optimization iteration.
            Passes in a GA instance named x in this func
            """

            # sum accumulator for standard deviation of a stage
            sum_stage_sd = 0  # stages -> individual gene

            for i in range(x.pop_size[1]):  # iterate through each gene/stage
                stage_mean = np.mean(x.population[:, i])
                squared_diffs = np.square(x.population[:, i] - stage_mean)
                mean_squared_diffs = np.mean(squared_diffs)  # mean of squared differences
                sum_stage_sd += np.sqrt(mean_squared_diffs)  # add standard deviation of this gene

            # Diversity of this population / generation -> average standard deviation of genes
            diversity = sum_stage_sd / x.pop_size[1]
            self.diversity.append(diversity)

            x.logger.info(self.diversity)

            # Update progress bar if it exists
            if pbar is not None:
                pbar.update(1)
            else:
                print("New generation!")

        # We must obtain or create an initial population for GA to work with.
        initial_population = self.get_initial_population(self.sol_per_pop, force_new_population_flag)

        # This informs GA when to end the optimization sequence. If blank, it will continue until the generation
        # iterations finish. Write "saturate_x" for the sequence to end after x generations of no improvement to
        # fitness. Write "reach_x" for the sequence to end after fitness has reached x.
        stop_criteria = self.settings.stopping_criteria

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
                                    on_generation=on_generation_callback,
                                    delay_after_gen=delay_after_generation,
                                    random_mutation_max_val=mutation_max_value,
                                    stop_criteria=str(stop_criteria))

    def get_initial_population(self, num_arrays_to_generate, force_new_population_flag) -> np.ndarray:
        """

        Acquire an array of valid driving speed arrays as a starting population for GA by either reading them
        from cache or generating a new set.

        :param num_arrays_to_generate: the number of "guess" driving speed arrays that must be obtained
        :param force_new_population_flag: force the creation of new arrays instead of reading a cached
        :return: an array of driving speed arrays with a length equal to `num_arrays_to_generate`
        :rtype: np.ndarray

        """

        population_file = population_directory / "initial_population.npz"
        arrays_from_cache = 0
        new_initial_population = None

        # Check if we can grab cached driving speed arrays
        if os.path.isfile(population_file) and not force_new_population_flag:
            try:
                with np.load(population_file) as population_data:
                    # We compare the hash value of the active Simulation model to the one that is cached
                    # because speeds that are valid for one model may not be valid for another (and the
                    # driving speed array length may also differ)
                    if population_data['hash_key'] == self.model.hash_key:
                        initial_population = np.array(population_data['population'])

                        # Check if the number of arrays needed and cached match. If we need more
                        # arrays than are cached, we can still use the cached arrays and just generate more.
                        if len(initial_population) == self.sol_per_pop:
                            return initial_population
                        else:
                            # In the case that there are more cached arrays then we need, slice off the excess.
                            new_initial_population = population_data['population'][:num_arrays_to_generate]
                            arrays_from_cache = len(new_initial_population)
            except zipfile.BadZipFile:
                arrays_from_cache = 0

        # If we need more arrays, generate the number of new arrays that we need
        if arrays_from_cache < num_arrays_to_generate:
            remaining_arrays_needed = num_arrays_to_generate - arrays_from_cache
            additional_arrays = self.generate_valid_speed_arrays(remaining_arrays_needed)
            if arrays_from_cache == 0:
                new_initial_population = additional_arrays
            else:
                new_initial_population = np.concatenate((new_initial_population, additional_arrays))

        # Cache the arrays we just generated with our active model's hash key
        with open(population_file, 'wb') as f:
            np.savez(f, hash_key=self.model.hash_key, population=new_initial_population)

        return new_initial_population

    def generate_valid_speed_arrays(self, num_arrays_to_generate: int) -> np.ndarray:
        """

        Generate a set of normalized driving speeds arrays that are valid for the active Simulation model
        using Perlin noise. Will return an array with num_arrays_to_generate valid arrays.

        :param int num_arrays_to_generate:
        :return: an array of `num_arrays_to_generate` driving speeds, valid for the active Simulation model.
        :rtype: np.ndarray

        """

        # These numbers were experimentally found to generate high fitness values in guess arrays
        # while having an acceptably low chance of not resulting in a successful simulation.
        max_speed_kmh: float = 40
        min_speed_kmh: float = 30

        # We will use Perlin noise to generate our guess arrays
        noise_generator = Noise()

        # Determine the length that our driving speed arrays must be
        length = self.model.get_driving_time_divisions()
        speed_arrays = []

        with tqdm(total=num_arrays_to_generate, file=sys.stdout, desc="Generating new initial population ", position=0,
                  leave=True) as pbar:
            # Generate a matrix of normalized Gaussian noise of size [length, num_arrays_to_generate]
            noise = noise_generator.get_gauss_noise_matrix(length, num_arrays_to_generate)

            x = 0

            while len(speed_arrays) < num_arrays_to_generate:
                # Read rows from the Gaussian noise matrix as a normalized driving speed array
                guess_speed = normalize(noise[x])

                # We generate just enough noise to be able to test num_arrays_to_generate speed arrays.
                # Thus, the following logic keeps careful track of the index because if we have even one
                # unsuccessful array, we'll need to generate more noise.
                if x >= len(noise) - 1:
                    noise = noise_generator.get_gauss_noise_matrix(length, num_arrays_to_generate)
                    x = 0

                else:
                    x += 1

                # We must denormalize the driving speeds array before simulating it.
                input_speed = rescale(guess_speed, max_speed_kmh, min_speed_kmh)
                self.model.run_model(speed=input_speed, plot_results=False, is_optimizer=True)

                # If the speed results in a successful simulation, add it to the population.
                if self.model.was_successful():
                    speed_arrays.append(normalize(input_speed, self.bounds[2], self.bounds[1]))
                    pbar.update(1)

        return np.array(speed_arrays)

    def fitness(self, ga_instance, solution, solution_idx) -> float:
        """

        This function is called by GA to evaluate the fitness of a given chromosome.
        The chromosome (driving speeds array) is fed as the driving speeds array and the
        model is simulated. The distance that can be travelled during the simulation
        duration is returned as the fitness of the chromosome.
        If the simulation results in
        state of charge dropping to 0% before the end, the distance travelled up until that point is used instead.

        NOTE: Once GA achieves solutions that consistently finish the race, then we must also factor in the
        time taken instead of solely the distance travelled.

        :param ga_instance: Required for GA but unused by this function
        :param solution: the chromosome that must be evaluated
        :param solution_idx: Required for GA but unused by this function
        :return: the fitness value of the chromosome
        :rtype: float

        """

        # Chromosomes are normalized, so must be denormalized before being fed to Simulation.
        solution_denormalized = denormalize(solution, self.bounds[2], self.bounds[1])
        distance_travelled, time_taken = self.func(speed=solution_denormalized, is_optimizer=True)

        # If Simulation did not complete successfully (SOC dropped below 0) then return the distance when that occurred.
        distance_travelled_real = distance_travelled if self.model.was_successful() \
            else self.model.get_distance_before_exhaustion()

        self.did_finish_race = True if distance_travelled_real == distance_travelled else False
        fitness = (691200 / time_taken) * (distance_travelled_real / 2466)
        # distance_travelled is scaled such that optimization REALLY prioritizes finishing the race
        distance_scaled = distance_travelled_real * self.fitness_sigmoid(distance_travelled_real)
        # optimization really likes even small reductions in time taken
        time_taken_scaled = time_taken / self.fitness_amplifier(time_taken)

        # combined_fitness = distance travelled (km) / time_taken (days) = distance travelled per day
        combined_fitness = distance_scaled / (time_taken_scaled / 86400)

        return fitness

    def maximize(self) -> np.ndarray:
        """

        Execute GA's maximization sequence.

        :return: Best solution identified by GA in km/h
        :rtype: np.ndarray

        """

        self.ga_instance.run()
        return self.output()

    def output(self) -> np.ndarray:
        """

        Get the best solution from GA.

        :return: best solution identified by GA in km/h
        :rtype: np.ndarray

        """

        # Get the optimal solution that GA found and its fitness value.
        solution, solution_fitness, solution_idx = self.ga_instance.best_solution()
        self.bestinput = denormalize(solution, self.bounds[2], self.bounds[1])

        # print("Parameters of the best solution : {solution}".format(solution=self.bestinput))
        # print("Fitness value of the best solution = {solution_fitness}".format(solution_fitness=solution_fitness))

        # Plot fitness compared to the generation index to how
        if self.output_hyperparameters:
            self.plot_fitness()

        # Set the fitness value of the hyperparameter configuration
        self.settings.set_fitness(solution_fitness)

        return self.bestinput

    def plot_fitness(self, save_graph: bool = True) -> None:
        """

        Plot the highest fitness value of each generation's population as a Fitness vs Generation graph.

        :param bool save_graph: set whether the graph should be saved to data/results directory.

        """

        # We keep track of the hyperparameter configuration index so that the filename matches the index
        # of the configuration on the `Hyperparameter Search` spreadsheet.
        sequence_index = GeneticOptimization.get_sequence_index(increment_index=False)

        graph_title = "sequence" + str(sequence_index)
        save_dir = None

        if save_graph:
            save_dir = results_directory / graph_title

        self.ga_instance.plot_fitness(title=graph_title, save_dir=save_dir)

    def write_results(self):
        """

        Write the hyperparameters of the current configuration, along with the resultant fitness
        value that the configuration achieved, to a CSV as one row.

        For the purposes of documenting the effectiveness of different hyperparameter configurations,
        we log each configuration and the resultant fitness and save the corresponding Fitness vs Generation
        graph. Both of the aforementioned items are saved the same hyperparameter index, which is stored
        in `register.json` and incremented for each subsequent hyperparameter configuration we attempt.

        """

        results_file = results_directory / "results.csv"
        with open(results_file, 'a') as f:
            writer = csv.writer(f)
            sequence_index: int = GeneticOptimization.get_sequence_index()
            output = self.settings.as_list()
            output.insert(0, str(sequence_index))
            output.append(str(self.did_finish_race))
            writer.writerow(output)

    @staticmethod
    def parse_csv_into_settings(csv_reader: csv.reader) -> list[OptimizationSettings]:
        """

        Parse data that has been read from a CSV file into hyperparameter configurations for GeneticOptimization.

        :param csv_reader: CSV data to be parsed
        :return: list of OptimizationSettings from the parsed hyperparameter configurations
        :rtype: list[OptimizationSettings]

        """

        settings_list = []

        for row in csv_reader:
            chromosome_size = int(row[0])
            parent_selection_type = OptimizationSettings.Parent_Selection_Type(row[1])
            generations_limit = int(row[2])
            num_parents = int(row[3])
            k_tournament = int(row[4])
            crossover_type = OptimizationSettings.Crossover_Type(row[5])
            elitism = int(row[6])
            mutation_type = OptimizationSettings.Mutation_Type(row[7])
            mutation_percent = float(row[8])
            max_mutation = float(row[9])
            stopping_criteria = OptimizationSettings.Stopping_Criteria(string=row[10])
            new_setting = OptimizationSettings(chromosome_size, parent_selection_type, generations_limit, num_parents,
                                               k_tournament, crossover_type, elitism, mutation_type, mutation_percent,
                                               max_mutation, stopping_criteria)
            settings_list.append(new_setting)

        return settings_list

    @staticmethod
    def get_sequence_index(increment_index=True) -> int:
        """

        Get the current index saved in the counter at `data/results/register.json`.

        :param increment_index: set to False in order to make this a read-only operation, otherwise the counter
        will be incremented.
        :return: the value stored in the counter
        :rtype: int

        """

        register_filepath = results_directory / "register.json"

        if not os.path.isfile(register_filepath):
            raise FileNotFoundError("Cannot find register file!")

        with open(register_filepath, "r") as file:
            register_data = json.load(file)

        x = register_data['x']
        x += 1

        if increment_index:
            GeneticOptimization.save_index(register_filepath, x)

        return x

    @staticmethod
    def save_index(register_filepath, index) -> None:
        """

        Save a new value in the counter.

        :param register_filepath: path to the register file
        :param index: value to save

        """

        with open(register_filepath, "w") as file:
            register_data = {
                "x": index
            }

            json.dump(register_data, file)

    @staticmethod
    def get_total_generations(settings_list: list[OptimizationSettings] = None) -> int:
        total: int = 0
        for settings in settings_list:
            total += settings.generation_limit
        return total


if __name__ == "__main__":
    register_file = results_directory / "register.json"
    GeneticOptimization.save_index(register_file, 26)
    print(GeneticOptimization.get_sequence_index(increment_index=False))

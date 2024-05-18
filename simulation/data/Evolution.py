import os
import pathlib
import time
import datetime
import git
import pandas as pd

from simulation.optimization.genetic import GeneticOptimization
from simulation.model.Simulation import Simulation


class Evolution:
    """

    Responsible for storing all the data related to the context, results, and optimization settings of an evolution.

    """
    def __init__(self, optimizer: GeneticOptimization, simulation_model: Simulation, fitness: tuple, results: pd.DataFrame):
        repo = git.Repo.init(pathlib.Path(os.getcwd()).parent)
        self.optimizer = optimizer

        # Context
        self.timestamp: datetime.datetime = datetime.datetime.fromtimestamp(time.time())
        self.username: str = repo.config_reader().get_value("user", "name")
        self.repo_commit: str = repo.git.rev_parse(repo.head.object.hexsha, short=10)
        self.is_dirty: bool = repo.is_dirty()

        # Simulation Attributes
        self.simulation_hash = simulation_model.hash_key
        # self.weather_hash = simulation_model.weather_hash
        # self.route_hash = simulation_model.route_hash
        self.race_type = simulation_model.race_type
        self.granularity = simulation_model.granularity
        self.lvs_power_loss = simulation_model.lvs_power_loss
        self.tick = simulation_model.tick
        self.simulation_duration = simulation_model.simulation_duration
        self.initial_battery_charge = simulation_model.initial_battery_charge
        self.start_hour = simulation_model.start_hour
        self.origin_coord = simulation_model.origin_coord
        self.dest_coord = simulation_model.dest_coord
        self.current_coord = simulation_model.current_coord

        # Optimization Settings
        self.chromosome_size: int = optimizer.settings.chromosome_size
        self.parent_selection_type = optimizer.settings.parent_selection_type
        self.generation_limit: int = optimizer.settings.generation_limit
        self.num_parents: int = optimizer.settings.num_parents
        self.k_tournament: int = optimizer.settings.k_tournament
        self.crossover_type = optimizer.settings.crossover_type
        self.elitism: int = optimizer.settings.elitism
        self.mutation_type = optimizer.settings.mutation_type
        self.mutation_percent: float = optimizer.settings.mutation_percent
        self.max_mutation: float = optimizer.settings.max_mutation
        self.stopping_criteria = optimizer.settings.stopping_criteria

        # Results
        self.best_fitness = fitness
        self.best_chromosome = optimizer.bestinput
        self.results = results
        self.diversity = optimizer.diversity
        self.stopping_point = optimizer.stopping_point

        # TODO:
        # self.fitness_over_generations = optimizer.fitness_over_generations


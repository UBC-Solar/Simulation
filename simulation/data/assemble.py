"""
Assemble data from local evolutions.
"""

import os
import csv
import dill
import pathlib
import numpy as np
import pandas as pd
from simulation.model.Simulation import Simulation
from simulation.data.Evolution import Evolution
from simulation.optimization.genetic import GeneticOptimization


class Assembler:
    def __init__(self, results_directory: str):
        self.results_directory: str = results_directory

        self.evolutions: list[str] = self.acquire_evolutions()

    def acquire_evolutions(self) -> list[str]:
        """
        Acquire paths to local evolutions.

        :return: list of evolution folders
        """
        dirs = [
            os.path.join(self.results_directory, directory)
            for directory in os.listdir(self.results_directory)
        ]
        evolution_folders = [
            directory
            for directory in dirs
            if (os.path.isdir(directory) and "__pycache__" not in directory)
        ]

        evolution_folders.sort(key=lambda x: x.split(os.sep)[-1])

        return evolution_folders

    def reacquire_evolutions(self) -> None:
        """
        Reacquire evolution folders.
        Useful if their names have been updated.
        """
        self.evolutions: list[str] = self.acquire_evolutions()

    @staticmethod
    def marshal_evolution(
        optimizer: GeneticOptimization, simulation_model: Simulation
    ) -> Evolution:
        """
        From an optimizer, generate an Evolution object containing the settings, context, and results.

        :param optimizer: optimizer that will be parsed
        :param simulation_model: results that will be saved
        :return: a new Evolution object containing the settings, context, and results of the evolution.
        """
        speeds: np.ndarray = optimizer.bestinput
        fitness = simulation_model.run_model(speeds, plot_results=False)

        # Get results
        results_arrays = simulation_model.get_results(
            [
                "speed_kmh",
                "distances",
                "state_of_charge",
                "delta_energy",
                "solar_irradiances",
                "wind_speeds",
                "gis_route_elevations_at_each_tick",
                "cloud_covers",
                "raw_soc",
            ]
        )
        results_labels = [
            "Speed (km/h)",
            "Distance (km)",
            "SOC (%)",
            "Delta Energy (J)",
            "Solar irradiance (W/m^2)",
            "Wind Speeds (km/h)",
            "Elevation (m)",
            "Cloud cover (%)",
            "Raw SOC (%)",
        ]

        # Pack results into a DataFrame
        results_df = pd.DataFrame(
            {label: array for label, array in zip(results_labels, results_arrays)}
        )

        return Evolution(optimizer, simulation_model, fitness, results_df)

    @staticmethod
    def get_current_evolution() -> int:
        """
        Obtain the number that should identify the next Evolution to be produced.

        :return: integer that should identify the next Evolution
        """
        with open(pathlib.Path(__file__).parent / "last_evolution.txt", "r") as file:
            return int(file.readline())

    @staticmethod
    def set_evolution_counter(new_value: int) -> None:
        """
        Set the number that should identify the next Evolution to be produced.

        :param new_value: integer that should identify the next Evolution to be produced
        """
        with open(pathlib.Path(__file__).parent / "last_evolution.txt", "w") as file:
            print(f"Writing {new_value}")
            file.write(str(new_value))

    @staticmethod
    def write_evolution_log(evolution_directory: str, evolution: Evolution):
        """
        From an ``evolution``, write the corresponding evolution log which
        describes the context, settings, and some results of an Evolution
        to a ``evolution_directory``.

        :param evolution_directory:
        :param evolution:
        :return:
        """
        with open(os.path.join(evolution_directory, "evolution_log.txt"), "x") as file:
            file.write(f" --- CONTEXT --- \n")
            file.write(f"TIMESTAMP:          {evolution.timestamp}\n")
            file.write(f"USER:               {evolution.username}\n")
            file.write(f"COMMIT:             {evolution.repo_commit}\n")
            file.write(f"SIMULATION ID:      {evolution.simulation_hash}\n")
            file.write(f"DIRTY REPO:         {evolution.is_dirty}\n")
            file.write(f"NOTES:               \n")
            file.write(f"\n")
            file.write(f" --- CONFIG --- \n")
            file.write(f"RACE:               {evolution.race_type}\n")
            file.write(f"GRANULARITY:        {evolution.granularity}\n")
            file.write(f"LVS POWER (W):      {evolution.lvs_power_loss}\n")
            file.write(f"TICK (s):           {evolution.tick}\n")
            file.write(f"DURATION (s):       {evolution.simulation_duration}\n")
            file.write(f"INITIAL CHARGE (%): {evolution.initial_battery_charge}\n")
            file.write(f"START HOUR:         {evolution.start_hour}\n")
            file.write(f"ORIGIN:             {evolution.origin_coord}\n")
            file.write(f"DESTINATION:        {evolution.dest_coord}\n")
            file.write(f"CURRENT:            {evolution.current_coord}\n")
            file.write(f"\n")
            file.write(f" --- OPTIMIZER --- \n")
            file.write(f"POPULATION SIZE:    {evolution.chromosome_size}\n")
            file.write(f"PARENT SELECTION:   {evolution.parent_selection_type}\n")
            file.write(f"GENERATIONS:        {evolution.generation_limit}\n")
            file.write(f"NUMBER OF PARENTS:  {evolution.num_parents}\n")
            file.write(f"K-TOURNAMENT SIZE:  {evolution.k_tournament}\n")
            file.write(f"CROSSOVER:          {evolution.crossover_type}\n")
            file.write(f"ELITISM:            {evolution.elitism}\n")
            file.write(f"MUTATION:           {evolution.mutation_type}\n")
            file.write(f"MAX MUTATION (%):   {evolution.mutation_percent}\n")
            file.write(f"STOPPING CRITERIA:  {evolution.stopping_criteria}\n")
            file.write(f"\n")
            file.write(f" --- RESULTS --- \n")
            file.write(
                f"FITNESS:            {' '.join(map(str, evolution.best_fitness))}\n"
            )
            file.write(
                f"CHROMOSOME:         {' '.join(map(str, evolution.best_chromosome))}\n"
            )
            file.write(
                f"DIVERSITY:          {' '.join(map(str, evolution.diversity))}\n"
            )
            file.write(f"STOPPING POINT:     {str(evolution.stopping_point)}")

    def write_results(self, evolution: Evolution, evolution_number: str):
        """

        Write the hyperparameters of the current configuration, along with the resultant fitness
        value that the configuration achieved, to a CSV as one row.

        For the purposes of documenting the effectiveness of different hyperparameter configurations,
        we log each configuration and the resultant fitness and save the corresponding Fitness vs Generation
        graph. Both of the aforementioned items are saved the same hyperparameter index, which is stored
        in `register.json` and incremented for each subsequent hyperparameter configuration we attempt.

        """

        # Legacy method to write results to a CSV
        results_file = os.path.join(self.results_directory, "results.csv")
        with open(results_file, "a") as f:
            writer = csv.writer(f)
            output = evolution.optimizer.settings.as_list()
            output.insert(0, evolution_number)
            writer.writerow(output)

    @staticmethod
    def write_chromosome_simulation(
        evolution_directory: str, evolution: Evolution
    ) -> None:
        """

        From an ``evolution``, pickle the object and save it onto the disk in ``evolution_directory``
        as ``results.pkl``.

        :raises FileExistsError: if there's already a ``results.pkl`` in ``evolution_directory``
        :param evolution_directory: the location to save the result
        :param evolution: the object that will be pickled
        """
        with open(os.path.join(evolution_directory, "results.pkl"), "xb") as file:
            dill.dump(evolution.results, file)

    @staticmethod
    def write_fitness_over_generation(
        evolution_directory: str, evolution: Evolution
    ) -> None:
        """
        From an ``evolution`` object, write the data for the "Fitness vs Generation" graph into a CSV
        in ``evolution_directory`` as ``fitness_vs_generation.csv``.

        :raises FileExistsError: if there's already a ``fitness_vs_generation.csv`` in ``evolution_directory``
        :param evolution_directory:
        :param evolution:
        """
        fitness_over_time = evolution.optimizer.ga_instance.best_solutions_fitness
        with open(
            os.path.join(evolution_directory, "fitness_vs_generation.csv"), "x"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(["Generation", "Fitness"])
            for i, fitness in enumerate(fitness_over_time):
                writer.writerow([i, fitness])

    def collect_local_results(self) -> pd.DataFrame:
        """
        Collect the data contained in the evolution logs of all local evolutions
        into a DataFrame.

        :return: DataFrame containing local evolution logs, indexed by evolution number
        """

        # Get all evolution directories, filtering out anything else
        dirs: list[str] = [
            os.path.join(self.results_directory, directory)
            for directory in os.listdir(self.results_directory)
        ]
        evolution_folders: list[str] = [
            directory
            for directory in dirs
            if (os.path.isdir(directory) and "__pycache__" not in directory)
        ]

        evolution_numbers = []
        evolution_logs: list[dict] = []

        # Walk through each evolution folder, collecting all the evolution logs
        for evolution_folder in evolution_folders:
            with open(
                os.path.join(evolution_folder, "evolution_log.txt"), "rt"
            ) as evolution_log:
                # Keep track of the evolution number by grabbing it from the folder name
                evolution_numbers.append(int(evolution_folder.split(os.sep)[-1]))

                # Parse the file into lines
                lines: list[str] = evolution_log.read().split("\n")
                # Go through the lines and filter out ones that aren't in the form "$FIELD: $DATA"
                valid_log_elements = [
                    item for item in lines if len(item.split(":")) == 2
                ]
                # Convert each element into a keypair and put it in a dictionary
                log_elements_dictionary = {
                    item.split(":")[0]: item.split(":")[1].strip()
                    for item in valid_log_elements
                }

                # Chromosome is too large (and not very relevant) to be in this CSV
                if "CHROMOSOME" in log_elements_dictionary.keys():
                    del log_elements_dictionary["CHROMOSOME"]

                evolution_logs.append(log_elements_dictionary)

        df = pd.DataFrame(evolution_logs)

        # Reindex to be indexed by evolution numbers
        df.index = evolution_numbers
        df.index.names = ["Evolution"]

        return df

    def write_evolution(self, evolution: Evolution) -> None:
        """

        Write the data contained by an ``evolution`` to the disk as an evolution folder.

        :param evolution: Evolution that will be written
        """
        evolution_number: int = Assembler.get_current_evolution()
        evolution_directory = os.path.join(
            self.results_directory, str(evolution_number)
        )

        os.makedirs(evolution_directory)

        Assembler.write_evolution_log(evolution_directory, evolution)
        self.write_results(evolution, str(evolution_number))
        Assembler.write_chromosome_simulation(evolution_directory, evolution)
        Assembler.write_fitness_over_generation(evolution_directory, evolution)

        Assembler.set_evolution_counter(evolution_number + 1)


if __name__ == "__main__":
    Assembler(
        "C:/Users/tamze/OneDrive/Documents/GitHub/Simulation/simulation/data/results"
    ).collect_local_results()

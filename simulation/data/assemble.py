import csv
import os.path

from simulation.data.Evolution import Evolution
from simulation.data.download import Downloader
from simulation.main import Simulation
from simulation.optimization.genetic import GeneticOptimization
import numpy as np
import pandas as pd
import dill


def marshal_evolution(optimizer: GeneticOptimization, simulation_model: Simulation) -> Evolution:
    speeds: np.ndarray = optimizer.bestinput
    fitness = simulation_model.run_model(speeds, plot_results=False)

    results_arrays = simulation_model.get_results(["speed_kmh", "distances", "state_of_charge", "delta_energy",
                                                   "solar_irradiances", "wind_speeds",
                                                   "gis_route_elevations_at_each_tick",
                                                   "cloud_covers", "raw_soc"])
    results_labels = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta Energy (J)",
                      "Solar irradiance (W/m^2)", "Wind Speeds (km/h)", "Elevation (m)",
                      "Cloud cover (%)", "Raw SOC (%)"]

    results_df = pd.DataFrame({label: array for label, array in zip(results_labels, results_arrays)})

    return Evolution(optimizer, simulation_model, fitness, results_df)


def get_current_evolution(results_directory: str) -> int:
    with open(os.path.join(results_directory, 'last_evolution.txt'), 'r') as file:
        return int(file.readline())


def set_evolution_counter(results_directory: str, new_value: int) -> None:
    with open(os.path.join(results_directory, 'last_evolution.txt'), 'w') as file:
        print(f"Writing {new_value}")
        file.write(str(new_value))


def write_evolution_log(evolution_directory: str, evolution: Evolution):
    with open(os.path.join(evolution_directory, "evolution_log.txt"), 'x') as file:
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
        file.write(f"FITNESS:            {evolution.best_fitness}\n")
        file.write(f"CHROMOSOME:         {evolution.best_chromosome}")


def write_results(results_directory: str, evolution: Evolution, evolution_number: str):
    """

    Write the hyperparameters of the current configuration, along with the resultant fitness
    value that the configuration achieved, to a CSV as one row.

    For the purposes of documenting the effectiveness of different hyperparameter configurations,
    we log each configuration and the resultant fitness and save the corresponding Fitness vs Generation
    graph. Both of the aforementioned items are saved the same hyperparameter index, which is stored
    in `register.json` and incremented for each subsequent hyperparameter configuration we attempt.

    """

    results_file = os.path.join(results_directory, "results.csv")
    with open(results_file, 'a') as f:
        writer = csv.writer(f)
        output = evolution.optimizer.settings.as_list()
        output.insert(0, evolution_number)
        writer.writerow(output)


def write_chromosome_simulation(evolution_directory: str, evolution: Evolution):
    with open(os.path.join(evolution_directory, 'results.pkl'), 'xb') as file:
        dill.dump(evolution.results, file)


def write_fitness_over_generation(evolution_directory: str, evolution: Evolution):
    fitness_over_time = evolution.optimizer.ga_instance.best_solutions_fitness
    with open(os.path.join(evolution_directory, 'fitness_vs_generation.csv'), 'x') as file:
        writer = csv.writer(file)
        writer.writerow(["Generation", "Fitness"])
        for i, fitness in enumerate(fitness_over_time):
            writer.writerow([i, fitness])


def collect_local_results(results_directory: str):
    dirs = [os.path.join(results_directory, directory) for directory in os.listdir(results_directory)]
    evolution_folders = [directory for directory in dirs if (os.path.isdir(directory) and '__pycache__' not in directory)]

    evolution_logs: list[dict] = []
    for evolution_folder in evolution_folders:
        with open(os.path.join(evolution_folder, 'evolution_log.txt'), 'rt') as evolution_log:
            lines: list[str] = evolution_log.read().split('\n')
            data = {item.split(':')[0]: item.split(':')[1].strip() for item in lines if len(item.split(':')) > 1}

            if 'CHROMOSOME' in data.keys():
                del data['CHROMOSOME']

            evolution_logs.append(data)

    df = pd.DataFrame(evolution_logs)
    df.index.names = ['Evolution']
    return df


def assemble_evolution(results_directory: str, evolution: Evolution):
    evolution_number: int = get_current_evolution(results_directory)
    evolution_directory = os.path.join(results_directory, str(evolution_number))

    os.makedirs(evolution_directory)

    write_evolution_log(evolution_directory, evolution)
    write_results(results_directory, evolution, str(evolution_number))
    write_chromosome_simulation(evolution_directory, evolution)
    write_fitness_over_generation(evolution_directory, evolution)

    set_evolution_counter(results_directory, evolution_number + 1)


def pull():
    downloader = Downloader()
    downloader.download_evolution_browser()
    downloader.download_evolution_browser()


def push():
    print("Hi!")


if __name__ == "__main__":
    collect_local_results('/Users/joshuariefman/Simulation/simulation/data/results')

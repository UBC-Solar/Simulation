import numpy as np
from simulation.optimization.genetic import GeneticOptimization
from simulation.utils import InputBounds
from physics.models.motor.advanced_motor import AdvancedMotor

from geometry import get_distances

class MicroSimulationOptimizer(GeneticOptimization):
    def __init__(
            self,
            mesh,
            gradients,
            trajectory_length,
            num_lateral_indices,
            speed_kmh,
            model: AdvancedMotor,
            settings=None,
            pbar=None,
            force_new_population_flag=False):

        # Override gene space for path optimization (e.g., 3 possible trajectories per segment)
        self.num_lateral_indices = num_lateral_indices
        self.speed_kmh = speed_kmh
        self.gradients = gradients
        self.trajectory_length = trajectory_length
        self.mesh = mesh

        super().__init__(
            model=model,
            bounds=InputBounds(),
            run_model=None,
            settings=settings,
            pbar=pbar,
            force_new_population_flag=force_new_population_flag,
        )

        self.ga_instance.gene_space = {"low": 0, "high": num_lateral_indices - 1, "step": 1}  # Discrete path indices

        # long run
        self.ga_instance.num_generations = 2000
        self.ga_instance.population_size = 250
        self.ga_instance.mutation_probability = 0.2
        self.ga_instance.stop_criteria = []  # disables early stopping

        # short run
        # self.ga_instance.num_generations = 500
        # self.ga_instance.population_size = 200
        # self.ga_instance.mutation_probability = 0.2
        # self.ga_instance.stop_criteria = []  # disables early stopping


    def generate_valid_arrays(self, num_arrays_to_generate: int) -> np.ndarray:
        """
        Generate valid path choice arrays (instead of speed arrays).
        Each gene represents a path index (e.g., 0, 1, or 2) at a trajectory point.
        """
        path_arrays = []

        while len(path_arrays) < num_arrays_to_generate:
            candidate = np.random.randint(0, self.num_lateral_indices, self.trajectory_length)
            path_arrays.append(candidate)

        return np.array(path_arrays)


    def get_initial_population(
        self, num_arrays_to_generate, force_new_population_flag
    ) -> np.ndarray:
        # return self.generate_valid_arrays(num_arrays_to_generate)
        return self.generate_valid_arrays(50)

    def get_trajectory_from_solution(self, solution):
        trajectory = [self.mesh[i][int(solution[i])] for i in range(len(solution))]
        return trajectory

    def fitness(self, ga_instance, solution, solution_idx) -> float:
        """
        Minimize total energy consumed by a path.
        """

        trajectory = np.array(self.get_trajectory_from_solution(solution))

        num_elements = len(solution)

        distances = get_distances(trajectory)
        distances_m = np.array(distances)

        tick_arr = np.zeros(num_elements)
        wind_speed_arr = np.zeros(num_elements)  # no wind

        # initialize speed array and calculate tick based on speed and distance
        speed_kmh_arr = np.full(num_elements, self.speed_kmh)
        speed_ms_arr = speed_kmh_arr / 3.6
        for index, d in enumerate(distances_m):
            tick_arr[index] = d / speed_ms_arr[index]

        # print(f"gradients: {self.gradients.shape}")
        # print(f"wind: {wind_speed_arr.shape}")
        # print(f"ticks: {tick_arr.shape}")
        # print(f"trajectory: {trajectory.shape}")

        energy_used, energy_cornering, gradients_arr, road_friction_forces, drag_forces, g_forces = self.model.calculate_energy_in(
                speed_kmh_arr,
                self.gradients,
                wind_speed_arr,
                tick_arr,
                trajectory
        )

        return -energy_used  # Minimize energy use

    def output(self) -> np.ndarray:
        """
        Get the best path solution (sequence of path indices).
        """
        solution, solution_fitness, solution_idx = self.ga_instance.best_solution()
        self.bestinput = solution
        self.settings.set_fitness(solution_fitness)

        print("reached final solution")
        return self.get_trajectory_from_solution(self.bestinput)

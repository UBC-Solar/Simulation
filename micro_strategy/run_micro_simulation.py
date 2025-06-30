import random
import numpy as np
import tomllib as toml
from geopy.distance import distance
import time
from pathlib import Path

from micro_strategy.geometry import get_distances
from micro_strategy.plotting import plot_mesh
from micro_strategy.micro_model_builder import MicroModelBuilder

from simulation.config import ConfigDirectory
from simulation.config import (
    InitialConditions,
    EnvironmentConfig,
    CarConfig,
)

from scipy.optimize import differential_evolution

def load_configs(competition_name = "FSGP", car_name: str = "BrightSide"):
    config_path = ConfigDirectory / f"initial_conditions_{competition_name}.toml"
    with open(config_path, "rb") as f:
        initial_conditions_data = toml.load(f)
        initial_conditions = InitialConditions.build_from(initial_conditions_data)

    #  ----- Load model parameters -----
    config_path = ConfigDirectory / f"settings_{competition_name}.toml"
    with open(config_path, "rb") as f:
        model_parameters_data = toml.load(f)
        environment_config = EnvironmentConfig.build_from(model_parameters_data)

    #  ----- Load car -----
    config_path = ConfigDirectory / f"{car_name}.toml"
    with open(config_path, "rb") as f:
        car_config_data = toml.load(f)
        car_config = CarConfig.build_from(car_config_data)

    return initial_conditions, environment_config, car_config


def latlon_to_meters(lat, lon):
    """Approximates local meters per degree at given latitude."""
    lat_m = distance((lat, lon), (lat + 0.0001, lon)).meters / 0.0001
    lon_m = distance((lat, lon), (lat, lon + 0.0001)).meters / 0.0001
    return lat_m, lon_m


def generate_lateral_mesh(trajectory, lateral_distance_meters, lateral_num_points):
    trajectory = np.array(trajectory)
    lateral_mesh = []

    for i in range(len(trajectory)):
        lat, lon = trajectory[i]

        lat_m, lon_m = latlon_to_meters(lat, lon)

        if i == 0:  # Forward difference for first point
            dlat, dlon = trajectory[i + 1] - trajectory[i]
        elif i == len(trajectory) - 1:  # Backward difference for last point
            dlat, dlon = trajectory[i] - trajectory[i - 1]
        else:  # Central difference for interior points
            dlat, dlon = trajectory[i + 1] - trajectory[i - 1]

        # Convert directional difference to meters
        dx = dlon * lon_m
        dy = dlat * lat_m

        # Normalize direction vector
        norm = np.sqrt(dx ** 2 + dy ** 2)
        if norm == 0:  # Avoid division by zero
            lateral_mesh.append([(lat, lon)]) 
            continue
        dx /= norm
        dy /= norm

        # Compute perpendicular vector (rotated 90 degrees)
        perp_dx = -dy
        perp_dy = dx

        # Store the trajectory point at the center of the row
        lateral_points = [(lat, lon)]

        for lateral_i in range(1, lateral_num_points + 1):
            left_lat = lat + (perp_dy * lateral_distance_meters * lateral_i) / lat_m
            left_lon = lon + (perp_dx * lateral_distance_meters * lateral_i) / lon_m

            right_lat = lat - (perp_dy * lateral_distance_meters * lateral_i) / lat_m
            right_lon = lon - (perp_dx * lateral_distance_meters * lateral_i) / lon_m

            lateral_points.insert(0, (left_lat, left_lon))
            lateral_points.append((right_lat, right_lon))

        lateral_mesh.append(lateral_points)

    return lateral_mesh


def get_random_trajectory(mesh):
    random_trajectory = []
    for i in range(len(mesh)):
        random_index = random.randint(0, len(mesh[0]) - 1)
        random_trajectory.append(mesh[i][random_index])
    return random_trajectory


def objective_trajectory_energy(
    x,
    mesh,
    gradients,
    motor_model,
    num_lateral_indices,
    speed_bounds,
):
    n = len(mesh)

    # Mutations aren't necessarily within optimizer bounds
    # Clip this array to avoid invalid speeds messing with the motor model
    speed_kmh = np.clip(x[n:], speed_bounds[0], speed_bounds[1])
    idx = np.rint(x[:n]).astype(int).clip(0, num_lateral_indices - 1)

    # Convert index array to mesh form
    path = [mesh[i][j] for i, j in enumerate(idx)]
    dists_m = np.array(get_distances(path))

    v_ms = speed_kmh / 3.6
    ticks = dists_m / v_ms
    winds = np.zeros_like(dists_m)

    energy = motor_model.calculate_energy_in(
        speed_kmh, gradients, winds, ticks, path, plotting=False
    )

    return np.sum(energy)


def optimize_trajectory(
    iterations,
    mesh,
    gradients,
    trajectory_length,
    num_lateral_indices,
    motor_model,
    speed_range=[.1, 100]
):
    lateral_index_bounds = [(0, num_lateral_indices - 1)] * trajectory_length
    speed_bounds = [(speed_range[0], speed_range[1])] * trajectory_length
    bounds = lateral_index_bounds + speed_bounds

    population_size = 20

    result = differential_evolution(
        objective_trajectory_energy,
        bounds,
        args=(mesh, gradients, motor_model, num_lateral_indices, speed_range),
        strategy="best1bin",
        popsize=population_size,
        maxiter=iterations,
        mutation=(0.6, 1.2),
        recombination=0.9,
        tol=0,                  # no early stopping based on convergence
        polish=True,
        disp=True,
        workers=-1,             # parallel evaluation
        seed=42
    )

    best_idx = np.rint(result.x[:len(mesh)]).astype(int).clip(0, num_lateral_indices - 1)
    best_path = [mesh[i][j] for i, j in enumerate(best_idx)]

    best_speeds = result.x[len(mesh):]

    return best_path, best_speeds


def run_motor_model(speed_kmh, distances_m, trajectory, environment_config, initial_conditions, car_config):
    num_elements = len(trajectory)
    if len(distances_m) != num_elements:
        raise RuntimeError("All arrays must have the same length.")

    tick_arr = np.zeros(num_elements)
    wind_speed_arr = np.zeros(num_elements) # no wind

    if isinstance(speed_kmh, (int, float)):
        speed_kmh_arr = np.full(num_elements, speed_kmh)
    else:
        speed_kmh_arr = np.asarray(speed_kmh)
        if speed_kmh_arr.shape[0] != num_elements:
            raise ValueError("speed_kmh array must match trajectory length.")

    speed_ms_arr = speed_kmh_arr / 3.6
    for index, d in enumerate(distances_m):
        tick_arr[index] = d / speed_ms_arr[index]

    micro_builder = (
        MicroModelBuilder()
        .set_environment_config(
            environment_config,
            rebuild_weather_cache=False,
            rebuild_route_cache=False,
            rebuild_competition_cache=False,
        )
        .set_initial_conditions(initial_conditions)
        .set_car_config(car_config)
    )
    micro_builder.compile()
    advanced_motor, gis = micro_builder.get()

    closest_gis_indices = np.arange(num_elements)
    gradients_arr = gis.get_gradients(closest_gis_indices)

    energies, energy_cornering, gradients_arr, road_friction_forces, drag_forces, g_forces = advanced_motor.calculate_energy_in(
        speed_kmh_arr, 
        gradients_arr, 
        wind_speed_arr, 
        tick_arr, 
        trajectory, 
        plotting="True"
    )

    return  energies, energy_cornering, road_friction_forces, drag_forces, g_forces, tick_arr, speed_kmh_arr, gradients_arr, advanced_motor


def main():
    project_root = Path(__file__).resolve().parent   
    output_dir = project_root / "optimization_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh_branch_length = 2

    initial_conditions, environment_config, car_config = load_configs()
    trajectory_FSGP = environment_config.competition_config.route_config.coordinates
    mesh = generate_lateral_mesh(trajectory_FSGP, 2, mesh_branch_length)
    random_trajectory = get_random_trajectory(mesh)

    num_lateral_indices = mesh_branch_length * 2 + 1

    distances = get_distances(random_trajectory)
    distances_m = np.array(distances)

    total_length_m = np.sum(distances_m)
    print(f"Total trajectory length: {total_length_m:.2f} meters ({total_length_m / 1000:.2f} km)")

    energy_consumed, cornering_work, road_friction_array, drag_forces, g_forces, ticks, speeds_kmh, gradients, advanced_motor = run_motor_model(
        speed_kmh=50,
        distances_m=distances_m,
        trajectory=random_trajectory,
        environment_config=environment_config,
        initial_conditions=initial_conditions,
        car_config=car_config,
    )

    start_time = time.time()

    optimized_trajectory, optimized_speeds = optimize_trajectory(
        iterations=5,
        mesh=mesh,
        gradients=gradients,
        trajectory_length=len(trajectory_FSGP),
        num_lateral_indices=num_lateral_indices,
        motor_model=advanced_motor
    )

    distances_m_op = np.array(get_distances(random_trajectory))

    energy_consumed_op, cornering_work_op, road_friction_array_op, drag_forces_op, g_forces_op, ticks_op, speeds_kmh_op, gradients_op, advanced_motor = run_motor_model(
        speed_kmh=optimized_speeds,
        distances_m=distances_m,
        trajectory=optimized_trajectory,
        environment_config=environment_config,
        initial_conditions=initial_conditions,
        car_config=car_config,
    )

    folium_map_optimized = plot_mesh(
        "energy",
        optimized_trajectory,
        mesh,
        distances_m_op,
        speeds_kmh_op,
        energy_consumed_op,
        ticks_op,
        cornering_work_op,
        gradients_op,
        road_friction_array_op,
        drag_forces_op,
        g_forces_op)

    folium_map_optimized.save(output_dir / "optimized_trajectory_energy.html")

    folium_map_optimized = plot_mesh(
        "speed",
        optimized_trajectory,
        mesh,
        distances_m_op,
        speeds_kmh_op,
        energy_consumed_op,
        ticks_op,
        cornering_work_op,
        gradients_op,
        road_friction_array_op,
        drag_forces_op,
        g_forces_op)

    folium_map_optimized.save(output_dir / "optimized_trajectory_speed.html")

    print("____Optimization Results____\n")
    print(f"Total Energy - Random Route:     {np.sum(energy_consumed):.2f} J")
    print(f"Total Energy - Optimized Route:  {np.sum(energy_consumed_op):.2f} J")
    print(f"Cornering Loss - Random Route:   {np.sum(cornering_work):.2f} J")
    print(f"Cornering Loss - Optimized Route:{np.sum(cornering_work_op):.2f} J")
    print(f"Drag Work - Random Route:        {np.sum(drag_forces * distances_m):.2f} J")
    print(f"Drag Work - Optimized Route:     {np.sum(drag_forces_op * distances_m_op):.2f} J")
    print(f"Avg G-Force - Random Route:      {np.mean(g_forces):.3f} g")
    print(f"Avg G-Force - Optimized Route:   {np.mean(g_forces_op):.3f} g")
    end_time = time.time()
    elapsed = end_time - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"Optimization Duration:           {minutes} min {seconds} sec")
    print("______________________________\n")

    np.save(output_dir / "optimized_trajectory.npy", np.array(optimized_trajectory))
    np.save(output_dir / "optimized_speeds.npy", np.array(optimized_speeds))




if __name__ == '__main__':
    main()

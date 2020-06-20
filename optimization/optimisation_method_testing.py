import simulation
import time as timer
import numpy as np
import datetime
from scipy.optimize import minimize, shgo, differential_evolution
import functools


def timeit(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        print(f">>> Running {func.__name__!r}... \n")
        start = timer.perf_counter()
        value = func(*args, **kwargs)
        stop = timer.perf_counter()
        run_time = stop - start
        print(f"Finished {func.__name__!r} in {run_time:.3f}s. \n")

    return wrapper_timer


def negative_distance_from_speed_array(speed_kmh):
    # ----- Simulation constants -----

    incident_sunlight = 1000
    initial_battery_charge = 0.90
    lvs_power_loss = 0
    max_speed = 104

    simulation_duration = 60 * 60 * 8
    tick = 1

    # ----- Speed array manipulations -----

    # TODO: replace clipping with optimization bounds or constraints
    speed_kmh = np.clip(speed_kmh, a_min=0, a_max=max_speed)
    speed_kmh = np.repeat(speed_kmh, 60 * 60)
    speed_kmh = np.insert(speed_kmh, 0, 0)

    # ----- Component initialisation -----

    basic_array = simulation.BasicArray(incident_sunlight)
    basic_array.set_produced_energy(0)

    basic_battery = simulation.BasicBattery(initial_battery_charge)

    basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

    basic_motor = simulation.BasicMotor()

    # ----- Energy calculations -----

    basic_array.update(tick)

    basic_lvs.update(tick)
    lvs_consumed_energy = basic_lvs.get_consumed_energy()

    basic_motor.calculate_power_in(speed_kmh)
    basic_motor.update(tick)
    motor_consumed_energy = basic_motor.get_consumed_energy()

    produced_energy = basic_array.get_produced_energy()
    consumed_energy = motor_consumed_energy + lvs_consumed_energy

    delta_energy = produced_energy - consumed_energy

    # ----- Array initialisation -----

    time = np.arange(0, simulation_duration + tick, tick, dtype='f4')

    # used to calculate the time the car was in motion
    tick_array = np.full_like(time, fill_value=tick, dtype='f4')
    tick_array[0] = 0

    # ----- Array calculations -----

    cumulative_delta_energy = np.cumsum(delta_energy)
    battery_variables_array = basic_battery.update_array(cumulative_delta_energy)

    # stores the battery SOC at each time step
    state_of_charge = battery_variables_array[0]
    state_of_charge[np.abs(state_of_charge) < 1e-03] = 0

    # when the battery is empty the car will not move
    speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh

    time_in_motion = np.logical_and(tick_array, state_of_charge) * tick

    time_taken = np.sum(time_in_motion)
    time_taken = str(datetime.timedelta(seconds=int(time_taken)))

    final_soc = state_of_charge[-1] * 100

    # ----- Target value -----

    distance = speed_kmh * (time_in_motion / 3600)
    distance_travelled = np.sum(distance) * -1

    return distance_travelled


@timeit
def nelder_mead_optimisation(initial_speed):
    # Result: works quite well
    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='Nelder-Mead',
                                options={'disp': True, 'xatol': 1e-1})

    print(f"{optimal_solution.message} \n")
    print(f"Optimal solution: {optimal_solution.x} \n")

    maximum_distance = np.abs(negative_distance_from_speed_array(optimal_solution.x))
    print(f"Maximum distance: {maximum_distance:.2f}km\n")


@timeit
def powell_optimisation(initial_speed):
    # Result: bit of a weird optimal result
    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='Powell',
                                options={'disp': True, 'xtol': 1e-1})

    print(f"{optimal_solution.message} \n")
    print(f"Optimal solution: {optimal_solution.x} \n")

    maximum_distance = np.abs(negative_distance_from_speed_array(optimal_solution.x))
    print(f"Maximum distance: {maximum_distance:.2f}km\n")


@timeit
def cg_optimization(initial_speed):
    # Result: straight up does not work
    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='CG',
                                options={'disp': True, 'gtol': 1e-5})

    print(f"{optimal_solution.message} \n")
    print(f"Optimal solution: {optimal_solution.x} \n")

    maximum_distance = np.abs(negative_distance_from_speed_array(optimal_solution.x))
    print(f"Maximum distance: {maximum_distance:.2f}km\n")


@timeit
def shgo_optimization():
    # Result: does not work well for our usage

    max_speed = 104
    bounds = [(1, max_speed), ] * 8

    optimal_solution = shgo(negative_distance_from_speed_array, bounds=bounds, n=10,
                            options={'ftol': 1e-12, 'disp': True})

    print(f"{optimal_solution.message} \n")
    print(f"Optimal solution: {optimal_solution.x} \n")

    maximum_distance = np.abs(negative_distance_from_speed_array(optimal_solution.x))
    print(f"Maximum distance: {maximum_distance:.2f}km\n")


@timeit
def differential_evolution_optimisation():
    # Result: takes a long time but works really well, maybe altering parameters will increase speed

    max_speed = 104
    bounds = [(20, max_speed), ] * 8

    optimal_solution = differential_evolution(negative_distance_from_speed_array, bounds=bounds,
                                              disp=True)

    print(f"{optimal_solution.message} \n")
    print(f"Optimal solution: {optimal_solution.x} \n")

    maximum_distance = np.abs(negative_distance_from_speed_array(optimal_solution.x))
    print(f"Maximum distance: {maximum_distance:.2f}km\n")

import datetime
import functools
import time as timer

import numpy as np
from scipy.optimize import minimize, shgo, differential_evolution

import simulation


# TODO: make objective function take simulation_duration as argument

# ----- Helper functions -----


def timeit(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        print(f">>> Running {func.__name__!r}... \n")
        start = timer.perf_counter()
        value = func(*args, **kwargs)
        stop = timer.perf_counter()
        run_time = stop - start
        print(f"Finished {func.__name__!r} in {run_time:.3f}s. \n")
        return value

    return wrapper_timer


# TODO: move this to a different file
def negative_distance_from_speed_array(speed_kmh):
    # ----- Simulation constants -----

    incident_sunlight = 1000
    initial_battery_charge = 0.90
    lvs_power_loss = 0
    max_speed = 104

    simulation_duration = 60 * 60 * 8
    tick = 1

    # ----- Speed array manipulations -----

    if len(speed_kmh) != (simulation_duration / 3600):
        raise Exception(f"Speed array of incorrect shape: {speed_kmh.shape}")

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


def display_result(res):
    print(f"{res.message} \n")
    print(f"Optimal solution: {res.x.round(2)} \n")
    print(f"Average speed: {np.mean(res.x).round(1)}km/h")

    maximum_distance = np.abs(negative_distance_from_speed_array(res.x))
    print(f"Maximum distance: {maximum_distance:.2f}km\n")


# ----- Optimization methods -----

@timeit
def nelder_mead_optimization(initial_speed=0):
    # Result: works quite well but depends quite a bit on initial condition

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='Nelder-Mead',
                                options={'disp': True, 'xatol': 1e-1})

    display_result(optimal_solution)
    return optimal_solution.x


@timeit
def powell_optimization(initial_speed=0):
    # Result: returns a bit of a weird optimal result

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='Powell',
                                options={'disp': True, 'xtol': 1e-1})

    display_result(optimal_solution)
    return optimal_solution.x


@timeit
def cg_optimization(initial_speed=0):
    # Result: straight up does not work

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='CG',
                                options={'disp': True, 'gtol': 1e-5})

    display_result(optimal_solution)
    return optimal_solution.x


@timeit
def shgo_optimization():
    # Result: does not work well for our usage

    max_speed = 104
    bounds = [(1, max_speed), ] * 8

    optimal_solution = shgo(negative_distance_from_speed_array, bounds=bounds, n=10,
                            options={'ftol': 1e-12, 'disp': True})

    display_result(optimal_solution)
    return optimal_solution.x


@timeit
def differential_evolution_optimization():
    # Result: takes a long time but works really well, maybe altering parameters will increase speed
    # a huge advantage here is that it doesn't take an initial condition

    max_speed = 104
    bounds = [(20, max_speed), ] * 8

    # may have to re-tune the mutation and recombination parameters in the future
    optimal_solution = differential_evolution(negative_distance_from_speed_array, bounds=bounds,
                                              disp=True, strategy="best1bin", atol=1e-2, mutation=(0.2, 0.5),
                                              popsize=15, recombination=0.9)

    display_result(optimal_solution)
    return optimal_solution.x


@timeit
def bfgs_optimization(initial_speed=0):
    # Result: does not work

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='BFGS',
                                options={'disp': True})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def l_bfgs_b_optimization(initial_speed=0):
    # Result: does not work

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='L-BFGS-B',
                                options={'disp': True, 'iprint': 99})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def tnc_optimization(initial_speed=0):
    # Result: fast and finds a remarkably accurate result provided
    # that the initial guess is kept low

    max_speed = 104
    bounds = [(20, max_speed), ] * 8

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='TNC', bounds=bounds,
                                options={'disp': True, 'mesg_num': 0, 'eta': 0.01, 'xtol': 0.005, 'ftol': 0.005,
                                         'maxCGit': 0})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def cobyla_optimization(initial_speed=0):
    # Result: scary fast and result is by far the most accurate
    # this is probably the best optimization method

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='COBYLA',
                                options={'disp': True})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def slsqp_optimization(initial_speed=0):
    # Result: runs but doesn't give an accurate answer

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='SLSQP',
                                options={'disp': True, 'iprint': 2})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def trust_constr_optimization(initial_speed=0):
    # Result: does not work

    max_speed = 104
    bounds = [(20, max_speed), ] * 8

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='trust-constr',
                                bounds=bounds, options={'disp': True, 'verbose': 1})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def dogleg_optimization(initial_speed=0):
    # Result: requires Jacobian of objective function and
    # I don't know how to compute that for our function

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='dogleg',
                                options={'disp': True, 'initial_trust_radius': 1, 'max_trust_radius': 1})

    display_result(optimal_solution)
    return optimal_solution


@timeit
def trust_ncg_optimization(initial_speed=0):
    # Result: Jacobian matrix of the objective function
    # is required here as well

    initial_guess = np.repeat(initial_speed, 8)
    optimal_solution = minimize(negative_distance_from_speed_array, x0=initial_guess, method='trust-ncg',
                                options={'disp': True, 'initial_trust_radius': 1, 'max_trust_radius': 1})

    display_result(optimal_solution)
    return optimal_solution


if __name__ == "__main__":
    cobyla_optimization()

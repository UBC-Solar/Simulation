import simulation
import datetime
import numpy as np
import time as timer

"""
Description: Given an input distance to travel,
determine the speed the car must travel
to make it within the day. [distance -> speed]
"""

# ----- Simulation input -----

input_distance = 300

start = timer.perf_counter()

tick = 1
simulation_duration = 60 * 60 * 9

# ----- Simulation constants -----

incident_sunlight = 1000
initial_battery_charge = 0.9
lvs_power_loss = 0

speed_increment = 1
max_speed = 104

# ----- Component initialisation -----

basic_array = simulation.BasicArray(incident_sunlight)
basic_array.set_produced_energy(0)

basic_battery = simulation.BasicBattery(initial_battery_charge)

basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

basic_motor = simulation.BasicMotor()

# ----- Array initialisation -----

time = np.arange(0, simulation_duration + tick, tick, dtype=np.uint32)

# stores the speeds that are considered in the simulation
speeds_simulated = np.arange(1, max_speed + speed_increment, speed_increment, dtype=np.uint8)

# creates a 2D array of simulated speeds at each time step
speed_kmh = np.meshgrid(time, speeds_simulated)[-1]

# used to calculate car's time in motion
tick_array = np.full_like(speed_kmh, fill_value=tick, dtype=np.uint32)
tick_array[:, 0] = 0

# ----- Energy calculations -----

basic_array.update(tick)

basic_lvs.update(tick)
lvs_consumed_energy = basic_lvs.get_consumed_energy()

basic_motor.calculate_power_in(speed_kmh)
basic_motor.update(tick)
motor_consumed_energy = basic_motor.get_consumed_energy()

produced_energy = basic_array.get_produced_energy()
consumed_energy = motor_consumed_energy + lvs_consumed_energy

# array that stores the energy transferred from/to battery for each simulated speed and each time step
delta_energy = produced_energy - consumed_energy

# ----- Array calculations -----

cumulative_delta_energy = np.cumsum(delta_energy, axis=1)

battery_variables_array = basic_battery.update_array(cumulative_delta_energy)

state_of_charge = battery_variables_array[0]
state_of_charge[np.abs(state_of_charge) < 1e-03] = 0

# when the battery SOC is empty, the car doesn't move
speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh

time_in_motion = np.logical_and(tick_array, state_of_charge) * tick
time_taken = np.sum(time_in_motion, axis=1)

distance = speed_kmh * (time_in_motion / 3600)

# stores total distance travelled at each time step for each speed simulated
distance = np.cumsum(distance, axis=1)

# stores the time taken for the entire distance to be travelled (in cases where the full distance is actually travelled)
time_taken_for_distance = np.argmax(distance > input_distance, axis=1)

# stores the indices for the speeds that allow for the full input distance to be traversed
speeds_successful_indices = np.nonzero(time_taken_for_distance)[0]

# ----- Simulation output -----

if len(speeds_successful_indices) == 0:
    print(f"\nNo solution found. Distance of {input_distance}km "
          f"untraversable in {datetime.timedelta(seconds=simulation_duration)} at any speed.\n")
else:
    optimal_speed_index = np.max(speeds_successful_indices)
    optimal_time_taken_index = time_taken_for_distance[optimal_speed_index]

    optimal_speed = speeds_simulated[optimal_speed_index]
    optimal_distance_travelled = distance[optimal_speed_index][optimal_time_taken_index]
    optimal_final_soc = state_of_charge[optimal_speed_index][optimal_time_taken_index]
    optimal_time_taken = time[optimal_time_taken_index]

    print(f"Simulation complete! \n\n"
          f"Optimal speed: {optimal_speed:.2f}km/h \n"
          f"Distance travelled: {optimal_distance_travelled:.2f}km \n"
          f"Final battery charge: {optimal_final_soc:.2f}% \n"
          f"Time taken: {datetime.timedelta(seconds=int(optimal_time_taken))} \n")

stop = timer.perf_counter()

print(f"Calculation time: {stop - start:.3f}s")

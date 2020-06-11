import simulation
import numpy as np
import datetime

"""
Description: Given a constant driving speed, find the range at the speed
before the battery runs out [speed -> distance]
"""

# ----- Simulation input -----

speed = float(input("Enter a speed (km/h): "))

# ----- Time parameters -----

simulation_duration = 60 * 60 * 9
tick = 1

# ----- Simulation constants -----

incident_sunlight = 1000
initial_battery_charge = 0.9
lvs_power_loss = 0
max_speed = 50

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

basic_motor.calculate_power_in(speed)
basic_motor.update(tick)
motor_consumed_energy = basic_motor.get_consumed_energy()

produced_energy = basic_array.get_produced_energy()
consumed_energy = motor_consumed_energy + lvs_consumed_energy

net_energy = produced_energy - consumed_energy

# ----- Array initialisation -----

time = np.linspace(0, simulation_duration, num=int(simulation_duration / tick) + 1, dtype='f4')

# stores speed of car at each time step
speed_kmh = np.full_like(time, fill_value=speed, dtype='f4')

# stores the amount of energy transferred from/to the battery at each time step
delta_energy = np.full_like(time, fill_value=net_energy, dtype='f4')

# used to calculate the time the car was in motion
tick_array = np.full_like(time, fill_value=tick, dtype='f4')
tick_array[0] = 0

# ----- Array calculations -----

cumulative_delta_energy = np.cumsum(delta_energy)
battery_variables = basic_battery.update_array(cumulative_delta_energy)

# stores the battery SOC at each time step
state_of_charge = battery_variables[0].round(3)

# when the battery is empty the car will not move
speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh

time_in_motion = np.logical_and(tick_array, state_of_charge) * tick

time_taken = np.sum(time_in_motion)
time_taken = str(datetime.timedelta(seconds=int(time_taken)))

final_soc = state_of_charge[-1] * 100 + 0.

# ----- Target value -----

distance = speed * (time_in_motion / 3600)
distance_travelled = np.sum(distance)

print(f"Time taken: {time_taken}\n"
      f"Speed: {speed}km/h\n"
      f"Maximum distance traversable: {distance_travelled:.2f}km\n"
      f"Final battery SOC: {final_soc:.2f}%\n")

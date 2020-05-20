import simulation
import numpy as np
import datetime

"""
Given an input time, determine the largest distance the car can travel in that time. 
Note: this example assumes constant speed throughout
"""

# TODO: add a momentum gradient descent algorithm to find optimal speed
# TODO: replace final_parameters dictionary with NumPy ndarray

# Time parameters
tick = 60

# Inputs
simulation_duration = int(60 * 60 * 9)  # 9 hours

# Simulation constants
incident_sunlight = 1000
initial_battery_charge = 0.9
battery_charge = initial_battery_charge
lvs_power_loss = 0

speed_increment = 1
max_speed_kmh = 50

# Outputs
final_parameters = dict()

for speed_kmh in range(1, max_speed_kmh + 1, speed_increment):
    distance_travelled = 0

    basic_array = simulation.BasicArray(incident_sunlight)
    basic_array.set_produced_energy(0)
    basic_battery = simulation.BasicBattery(initial_battery_charge)
    basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)
    basic_motor = simulation.BasicMotor()

    # run the simulation at a specific speed
    for time in range(tick, simulation_duration + tick, tick):

        basic_array.update(tick)
        produced_energy = basic_array.get_produced_energy()
        basic_lvs.update(tick)
        lvs_consumed_energy = basic_lvs.get_consumed_energy()
        basic_motor.update(tick)
        basic_motor.calculate_power_in(speed_kmh)
        motor_consumed_energy = basic_motor.get_consumed_energy()
        basic_battery.charge(produced_energy)

        try:
            basic_battery.discharge(lvs_consumed_energy)
            basic_battery.discharge(motor_consumed_energy)
            basic_battery.update(tick)

        # battery is empty
        except Exception as exp:
            # start simulation at next speed
            break

        # battery still has some charge in it
        else:
            # calculates the new distance that the car has moved
            distance_travelled += speed_kmh * (tick / 3600)

            # Ensures that the simulation doesn't run completely when the battery charge reaches equilibrium
            if battery_charge == basic_battery.get_state_of_charge() and basic_battery.is_empty() is not True:
                print(f"Equilibrium reached at speed {speed_kmh}km/h.\n")
                distance_travelled = speed_kmh * (simulation_duration / 3600)
                break

        finally:
            battery_charge = basic_battery.get_state_of_charge()

        if time % 60 == 0:
            print(f"Time: {time} sec / {str(datetime.timedelta(seconds=time))}")
            print(f"Car speed: {round(speed_kmh, 2)}km/h")
            print(f"Distance travelled: {round(distance_travelled, 3)}km")
            print(f"Battery SOC: {round(battery_charge * 100, 3)}%\n")

    final_parameters[speed_kmh] = distance_travelled

max_distance = round(max(final_parameters.values()), 2)
optimal_speed = round(max(final_parameters, key=final_parameters.get), 2)

print(f"Simulation complete! Maximum traversable distance in {simulation_duration / 3600}hrs is "
      f"{max_distance}km at speed {optimal_speed}km/h.")

import simulation

"""
Given an input time, determine the largest distance the car can travel in that time.

"""

# TODO: add a momentum gradient descent algorithm to find optimal speed

# Time parameters
tick = 60

# Inputs
simulation_duration = 60 * 60 * 6  # 9 hours

# Variables
speed_kmh = 1

# Simulation constants
incident_sunlight = 1000
initial_battery_charge = 0.9
battery_charge = initial_battery_charge
lvs_power_loss = 0
speed_increment = 1
max_speed_kmh = 50

# Flags
simulation_complete = False

# Outputs
final_distance_travelled = 0

while speed_kmh < max_speed_kmh and simulation_complete is False:

    speed_kmh += speed_increment

    current_distance_travelled = 0

    basic_array = simulation.BasicArray(incident_sunlight)
    basic_array.set_produced_energy(0)

    basic_battery = simulation.BasicBattery(initial_battery_charge)

    basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

    basic_motor = simulation.BasicMotor()

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

        except Exception as exp:  # battery empty
            break

        else:  # battery still has some charge in it
            current_distance_travelled = speed_kmh * (time / 3600)

            if battery_charge == basic_battery.get_state_of_charge() and basic_battery.get_state_of_charge() > 0.01:
                print(f"Equilibrium reached at speed {speed_kmh}km/h.\n")
                final_distance_travelled = current_distance_travelled
                break

        finally:
            battery_charge = basic_battery.get_state_of_charge()

        if time % 60 == 0:
            print(f"Time: {time} sec / {time / 60} mins")
            print(f"Car speed: {round(speed_kmh, 2)}km/h")
            print(f"Distance travelled: {round(current_distance_travelled, 3)}km")
            print(f"Battery SOC: {round(battery_charge * 100, 3)}%\n")

    if final_distance_travelled > current_distance_travelled:
        simulation_complete = True
        break
    else:
        final_distance_travelled = current_distance_travelled

print(f"Simulation complete! Maximum traversable distance in {simulation_duration / 3600}hrs is "
      f"{final_distance_travelled}km at speed {speed_kmh - speed_increment}km/h.")

# TODO: gives wrong speed here

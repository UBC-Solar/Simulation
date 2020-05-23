import simulation
import datetime
import math

"""
Description: Given an input distance to travel, 
determine the speed the car must travel 
to make it within the day [distance -> speed]

"""

# Time parameters
tick = 1  # in seconds
simulation_duration = 60 * 60 * 9  # 9 hours

# Simulation constants
incident_sunlight = 1000
initial_battery_charge = 0.9
lvs_power_loss = 0
speed_increment = 1
max_speed_kmh = 50  # is in km/h

# Simulation inputs
distance = float(input("Enter distance to travel: "))  # in kilometers

# Flags
simulation_complete = False

optimal_solution = ()

# Minimum speed that the car must go to cover the given distance in the given time
speed_kmh = math.ceil(distance / (simulation_duration / 3600))

# Runs the simulation at each speed
while speed_kmh <= max_speed_kmh and simulation_complete is False:

    distance_travelled = 0

    # Initialise simulation
    basic_array = simulation.BasicArray(incident_sunlight)
    basic_array.set_produced_energy(0)

    basic_battery = simulation.BasicBattery(initial_battery_charge)

    basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

    basic_motor = simulation.BasicMotor()

    for time in range(tick, simulation_duration + tick, tick):  # for every time interval

        # Perform energy exchanges between components (this whole mechanism needs to be improved)
        basic_array.update(tick)
        produced_energy = basic_array.get_produced_energy()

        basic_lvs.update(tick)
        lvs_consumed_energy = basic_lvs.get_consumed_energy()

        basic_motor.update(tick)
        basic_motor.calculate_power_in(speed_kmh)
        motor_consumed_energy = basic_motor.get_consumed_energy()

        basic_battery.charge(produced_energy)

        try:  # try removing some energy from the battery
            basic_battery.discharge(lvs_consumed_energy)
            basic_battery.discharge(motor_consumed_energy)
            basic_battery.update(tick)

        except simulation.BatteryEmptyError as exc:  # if the battery is empty
            simulation_complete = True
            break

        else:  # if the battery still has some charge in it
            distance_travelled += speed_kmh * (tick / 3600)

            if distance_travelled >= distance:
                optimal_solution = (
                    round(speed_kmh, 1), round(distance_travelled, 2),
                    round(basic_battery.get_state_of_charge() * 100, 2),
                    round(time / 3600, 2))
                break

        finally:
            battery_charge = basic_battery.get_state_of_charge()

        # prints simulation information every 60 seconds
        if time % 60 == 0:
            print(f"Time: {time} sec / {str(datetime.timedelta(seconds=time))}")
            print(f"Car speed: {round(speed_kmh, 2)}km/h")
            print(f"Distance travelled: {round(distance_travelled, 3)}km")
            print(f"Battery SOC: {round(battery_charge * 100, 3)}%\n")

    speed_kmh += speed_increment


if len(optimal_solution) > 0:
    optimal_speed, final_distance_travelled, final_battery_charge, time_taken = optimal_solution

    print("Simulation successful! Optimal solution found.\n")
    print("-------- Optimal solution --------")
    print(f"Optimal speed: {optimal_speed}km/h \n"
          f"Distance travelled: {final_distance_travelled}km \n"
          f"Final battery charge: {final_battery_charge}% \n"
          f"Time taken: {str(datetime.timedelta(hours=time_taken))}")

else:
    print(f"No solution found. Distance of {distance}km "
          f"untraversable in {str(datetime.timedelta(seconds=simulation_duration))} at any speed.")

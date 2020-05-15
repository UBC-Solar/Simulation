import simulation

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
distance = 200  # in kilometers

# Flags
simulation_complete = False

optimal_solution = ()

# Minimum speed that the car must go to cover the given distance in the given time
speed_kmh = round(distance / (simulation_duration / 3600))

# Runs the simulation at each speed
while speed_kmh < max_speed_kmh and simulation_complete is False:

    distance_travelled = 0
    speed_kmh += speed_increment

    # Initialise simulation
    basic_array = simulation.BasicArray(incident_sunlight)
    basic_array.set_produced_energy(0)

    basic_battery = simulation.BasicBattery(initial_battery_charge)

    basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

    basic_motor = simulation.BasicMotor()

    for time in range(tick, simulation_duration, tick):  # for every time interval

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

        except Exception as exp:  # if the battery is empty
            simulation_complete = True
            break

        else:  # if the battery still has some charge in it
            distance_travelled = speed_kmh * (time / 3600)

            if distance_travelled >= distance:
                optimal_solution = (
                    round(speed_kmh, 1), round(distance_travelled, 2),
                    round(basic_battery.get_state_of_charge() * 100, 2),
                    round(time / 3600, 2))
                break

        finally:
            basic_battery.update(tick)
            battery_charge = basic_battery.get_state_of_charge()

        if time % 60 == 0:
            print("Time: {} sec / {} mins".format(time, time / 60))
            print("Car speed: {}km/h".format(round(speed_kmh, 2)))
            print("Distance travelled: {}km".format(round(distance_travelled, 3)))
            print("Battery SOC: {}%\n".format(round(battery_charge * 100, 3)))

if len(optimal_solution) > 0:
    print("Simulation successful! Optimal solution found.\n")
    print("-------- Optimal solution --------")
    print("Optimal speed: {0}km/h\nDistance travelled: {1}km \nFinal battery charge: {2}% \nTime taken {3}hrs".format(
        *optimal_solution))

else:
    print("No solution found. Distance of {}km untraversable in {}hrs at any speed.".format(distance,
                                                                                            simulation_duration / 3600))

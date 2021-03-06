import simulation
import datetime

"""
Description: Given an input time, determine the largest distance the car can travel in that time. [time -> distance] 
Note: this example assumes constant speed throughout
"""

# Time parameters
tick = 1

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

    # Run the simulation at a specific speed
    for time in range(tick, simulation_duration + tick, tick):

        basic_array.update(tick)
        produced_energy = basic_array.get_produced_energy()
        basic_lvs.update(tick)
        lvs_consumed_energy = basic_lvs.get_consumed_energy()
        basic_motor.update(tick)
        basic_motor.calculate_power_in(speed_kmh)
        motor_consumed_energy = basic_motor.get_consumed_energy()
        basic_battery.charge(produced_energy)

        # tries to remove some energy from the battery
        try:
            basic_battery.discharge(lvs_consumed_energy)
            basic_battery.discharge(motor_consumed_energy)
            basic_battery.update(tick)

        # Battery is empty
        except simulation.BatteryEmptyError:
            break

        # Battery still has some charge in it
        else:
            distance_travelled += speed_kmh * (tick / 3600)

            # Ensures that the simulation doesn't run completely when the battery charge reaches equilibrium
            if battery_charge == basic_battery.get_state_of_charge() and basic_battery.is_empty() is not True:
                print(f"Equilibrium reached at speed {speed_kmh}km/h.\n")
                distance_travelled = speed_kmh * (simulation_duration / 3600)
                break

        finally:
            battery_charge = basic_battery.get_state_of_charge()

        if time % 60 == 0:
            print(f"Time: {time} sec / {datetime.timedelta(seconds=time)}")
            print(f"Car speed: {speed_kmh:.2f}km/h")
            print(f"Distance travelled: {distance_travelled:.2f}km")
            print(f"Battery SOC: {float(battery_charge) * 100:.3f}%\n")

    final_parameters[speed_kmh] = distance_travelled

max_distance = round(max(final_parameters.values()), 2)
optimal_speed = round(max(final_parameters, key=final_parameters.get), 2)

print(f"Simulation complete! Maximum traversable distance in {datetime.timedelta(seconds=simulation_duration)} is "
      f"{max_distance}km at speed {optimal_speed}km/h.")

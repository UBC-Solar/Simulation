import simulation
import datetime
import sys
from simulation.common.helpers import timeit

"""
Description: Given a constant driving speed, find the range at the speed
before the battery runs out [speed -> distance]
"""

# TODO: make it so that previous values are logged into a numpy array and maybe written to an npz file
# TODO: wrap this in a function definition
# TODO: create simulation result class?
# TODO: create simulation history class?
# TODO: run this function on a fixed time scale


@timeit
def max_distance_from_speed(speed):
    # Time parameters
    tick = 60

    # Simulation constants
    incident_sunlight = 1000
    initial_battery_charge = 0.90
    battery_charge = initial_battery_charge
    lvs_power_loss = 0
    max_speed = 50

    # Inputs

    while True:
        # speed_kmh = int(input("Enter a speed (km/h): "))
        speed_kmh = speed

        if 0 < speed_kmh <= max_speed:
            break
        else:
            print(f"Input value out of correct range. Must be between 0km/h and {max_speed}km/h.")

    distance_travelled = 0

    basic_array = simulation.BasicArray()
    basic_array.set_produced_energy(0)
    basic_battery = simulation.BasicBattery(initial_battery_charge)
    basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)
    basic_motor = simulation.BasicMotor()

    time = tick

    while True:

        # Energy transfers (which will be replaced)
        basic_array.update(tick)
        produced_energy = basic_array.get_produced_energy()
        basic_lvs.update(tick)
        lvs_consumed_energy = basic_lvs.get_consumed_energy()
        basic_motor.update(tick)
        basic_motor.calculate_power_in(speed_kmh, 0)
        motor_consumed_energy = basic_motor.get_consumed_energy()
        basic_battery.charge(produced_energy)

        try:
            basic_battery.discharge(lvs_consumed_energy)
            basic_battery.discharge(motor_consumed_energy)
            basic_battery.update(tick)

        except simulation.BatteryEmptyError:
            break

        else:
            distance_travelled += speed_kmh * (tick / 3600)

            if battery_charge == basic_battery.get_state_of_charge() and basic_battery.is_empty() is not True:
                print(f"Battery charge equilibrium reached at speed {speed_kmh}km/h. "
                      f"Maximum traversable distance is infinite.")
                sys.exit(1)

        finally:
            battery_charge = basic_battery.get_state_of_charge()

        if time % 60 == 0:
            print(f"Time: {time} sec / {str(datetime.timedelta(seconds=time))}")
            print(f"Car speed: {round(speed_kmh, 2)}km/h")
            print(f"Distance travelled: {round(distance_travelled, 3)}km")
            print(f"Battery SOC: {round(battery_charge * 100, 3)}%\n")

        time += tick

    print(f"Speed: {speed_kmh}km/h \n"
          f"Maximum distance traversable: {round(distance_travelled, 2)}km \n"
          f"Time taken: {str(datetime.timedelta(seconds=time))} \n")


max_distance_from_speed(23)

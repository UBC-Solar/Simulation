import simulation
import matplotlib.pyplot as plt

#ticks are in seconds
tick = 1
sim_duration = 60 * 60 * 6
speed_kmh = 60

#Initialize all simulation classes
incident_sunlight = 1000
initial_battery_charge = 0.9
lvs_power_loss = 0

basic_array = simulation.BasicArray(incident_sunlight)
basic_array.set_produced_energy(0)

basic_battery = simulation.BasicBattery(initial_battery_charge)

basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

basic_motor = simulation.BasicMotor()

#For plotting purposes
batt_charge = []
batt_voltage = []
time = []

for i in range(sim_duration):

    #Get produced energy from arrays
    basic_array.update(tick)
    produced_energy = basic_array.get_produced_energy()
    
    #Get consumed energy from LVS
    basic_lvs.update(tick)
    lvs_consumed_energy = basic_lvs.get_consumed_energy()

    #Get consumed energy from motor
    basic_motor.update(tick)
    basic_motor.calculate_power_in(speed_kmh)
    motor_consumed_energy = basic_motor.get_consumed_energy()

    #Add up energy balance on the battery
    basic_battery.update(tick)
    basic_battery.charge(produced_energy)
    basic_battery.discharge(lvs_consumed_energy)
    basic_battery.discharge(motor_consumed_energy)

    battery_energy = basic_battery.get_stored_energy()
    battery_charge = basic_battery.get_state_of_charge()
    battery_voltage = basic_battery.get_output_voltage()

    #For plotting purposes, sample every minute
    if i % 60 == 0:
        batt_charge.append(battery_charge)
        batt_voltage.append(battery_voltage)
        time.append(int(i / 60))

#Plot SOC vs time curve
plt.plot(time, batt_charge)
plt.xlabel("time in minutes")
plt.ylabel("% SOC")
plt.ylim(0, 1.0)
plt.title("% SOC vs time at {} kmh".format(speed_kmh))
plt.show()


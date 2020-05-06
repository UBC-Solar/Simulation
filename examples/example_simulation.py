import simulation

tick = 1

#Initialize all simulation classes
incident_sunlight = 1000
initial_battery_charge = 0.8
lvs_power_loss = 0
speed_kmh = 30

basic_array = simulation.BasicArray(incident_sunlight)
basic_array.set_produced_energy(0)

basic_battery = simulation.BasicBattery(initial_battery_charge)

basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

basic_motor = simulation.BasicMotor()

#No regen for now
#basic_regen = simulation.BasicRegen()

for i in range(10):

    basic_array.update(tick)
    produced_energy = basic_array.get_produced_energy()

    print("energy produced by arrays: {} J".format(produced_energy))

    basic_lvs.update(tick)
    lvs_consumed_energy = basic_lvs.get_consumed_energy()

    print("energy consumed by LVS: {} J".format(lvs_consumed_energy))

    basic_motor.update(tick)
    basic_motor.calculate_power_in(speed_kmh)
    motor_consumed_energy = basic_motor.get_consumed_energy()

    print("energy consumed by motor controller: {} J".format(motor_consumed_energy))
    
    basic_battery.update(tick)
    basic_battery.charge(produced_energy)
    basic_battery.discharge(lvs_consumed_energy)
    if basic_battery.is_empty():
        print("WARNING: battery is empty")
    basic_battery.discharge(motor_consumed_energy)
    if basic_battery.is_empty():
        print("WARNING: battery is empty")

    battery_energy = basic_battery.get_stored_energy()
    battery_charge = basic_battery.get_state_of_charge()
    battery_voltage = basic_battery.get_output_voltage()

    print("battery_energy: {} J".format(battery_energy * 3600))
    print("battery_charge: {} %".format(battery_charge*100))
    print("battery_voltage: {} V".format(battery_voltage))

    #No regen for now
    #basic_regen.update(1)
    
    

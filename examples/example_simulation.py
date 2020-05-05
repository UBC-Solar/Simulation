import simulation

basic_array = simulation.BasicArray()
basic_battery = simulation.BasicBattery(0)
basic_lvs = simulation.BasicLVS()
basic_motor = simulation.BasicMotor()
basic_regen = simulation.BasicRegen()

for i in range(10):
    
    basic_array.update(1)
    basic_battery.update(1)
    basic_lvs.update(1)
    basic_motor.update(1)
    basic_regen.update(1)

    print("hello world")
    
        
    
    
    

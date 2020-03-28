from simulation.battery.basic_battery import BasicBattery

DayBreakBattery = BasicBattery(initial_energy=4467, max_current_capacity=48.75, max_energy_capacity=4467)     

print(DayBreakBattery)    

DayBreakBattery.discharge(500)          # removes 500Wh of energy from the battery
DayBreakBattery.update()                # updates the battery variables

print(DayBreakBattery)      
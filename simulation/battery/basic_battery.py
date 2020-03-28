from simulation.battery.base_battery import BaseBattery


class BasicBattery(BaseBattery):
    def __init__(self):
        super().__init__(initial_energy=4467, max_current_capacity=48.75, max_energy_capacity=4467)     # i'm pretty sure this is the wrong place to put these arguments

        self.state_of_charge = 1
        self.depth_of_discharge = 1 - self.state_of_charge
        self.voltage = self.calculate_voltage(discharge_capacity=0)

        self.max_voltage = 117.6
        self.min_voltage = 70

    def calculate_discharge_capacity(self, energy):                         
        return (-117.6 + pow(13829.76 - 1.952 * energy, 0.5)) / (-0.976)

    def calculate_state_of_charge(self, discharge_capacity):
        return 1 - (discharge_capacity / 48.75)

    def calculate_voltage(self, discharge_capacity):
        return 117.6 - 0.488*(discharge_capacity)

    # TODO: make it so that I don't need to call self.update() after calling self.discharge() every time

    def update(self, tick=1):     # updates relevant battery variables
    
        discharge_capacity = self.calculate_discharge_capacity(self.max_energy_capacity - self.stored_energy)
        self.state_of_charge = self.calculate_state_of_charge(discharge_capacity)
        self.voltage = self.calculate_voltage(discharge_capacity)


DayBreakBattery = BasicBattery()     

DayBreakBattery.status_report()         

DayBreakBattery.discharge(500)          # removes 500Wh of energy from the battery
DayBreakBattery.update()                # updates the battery variables

DayBreakBattery.status_report()         

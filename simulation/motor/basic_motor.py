from simulation.motor.base_motor import BaseMotor

class BasicMotor(BaseMotor):

    def __init__(self):

        super().__init__()

        #Instantaneous voltage supplied by the battery to the motor controller
        self.dc_v = 0
        
        #Instantaneous current supplied by the battery to the motor controller
        self.dc_i = 0

        self.e_mc = 0.7 #motor controller efficiency, subject to change
        self.e_m = 0.7  #motor efficiency, subject to change
   
    #Calculates the power transferred to the wheel by the motor and the motor controller 
    def calculate_power_out(self):

        power_in = self.dc_v * self.dc_i
        power_controller = power_in * self.e_mc

        #alternatively, power_controller = sqrt(3) / 2 * Vrms * Irms
        power_out = power_controller * self.e_m

        #alternatively, power_out = torque * Revolutions/min = Force* V_car 
        #torque = rwheel * Forcewheel, RPM = V/rwheel

        return power_out

    #For the motor, the energy consumed by the motor/motor controller depends on the voltage and
    #   current supplied by the battery to the motor controller
    def update_motor_input(self, dc_v, dc_i):
    
        self.dc_v = dc_v
        self.dc_i = dc_i

    def update(self, tick):         
        #For the motor, the update tick calculates a value for the energy expended in a period of
        #   time

        self.consumed_energy = self.calculate_power_out() * tick

    #test 
    #input dc_v = 5, dc_c = 2 , wth e_mc = 0.7 and e_m = 0.7 , expected output 4.9 W
    #testex =  calculate_pout(5, 2)
    #print(testex)

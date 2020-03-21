from abc import ABC, abstractmethod

class Motor_Power(BaseMotor):
    #power calculations for motor 

    
    def calculate_pout(dc_v, dc_c):
        e_mc = 0.7 #motor controller efficiency, subject to 
        e_m = 0.7 #motor efficiency, subject to change
        power_in = dc_v * dc_c 
        power_controller = power_in * e_mc
        #alternatively, power_controller = sqrt(3) / 2 * Vrms * Irms
        power_out = power_controller * e_m
        #alternatively, power_out = torque * Revolutions/min = Force* V_car 
        #torque = rwheel * Forcewheel, RPM = V/rwheel
        return power_out 
    
    def update(self,tick) 

    #test 
    #input dc_v = 5, dc_c = 2 , wth e_mc = 0.7 and e_m = 0.7 , expected output 4.9 W
    testex =  calculate_pout(5, 2)
    print(testex)
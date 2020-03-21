from abc import ABC, abstractmethod

class Motor_Power(BaseMotor):
    #power calculations for motor 

    import numpy as np
    import math
    import sys

    e_mc = 0.7 #motor controller efficiency, subject to 
    e_m = 0.7 #motor efficiency, subject to change

    DC_voltage = 0 #dc voltage in v
    DC_current = 0 #dc current in A

    def calculate_pout(dc_v, dc_c):
        power_in = dc_v * dc_c 
        power_controller = power_in * e_mc
        #alternatively, power_controller = sqrt(3) / 2 * Vrms * Irms
        power_out = power_controller * e_m
        #alternatively, power_out = torque * Revolutions/min = Force* V_car 
        #torque = rwheel * Forcewheel, RPM = V/rwheel
        return power_out 
    
    def update(self,tick) 

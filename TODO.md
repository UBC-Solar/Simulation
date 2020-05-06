#TODO

##David Specifically


##Battery

- fix usage of variables in base_battery: make them parameterized.

- fix/handle behaviour when out of charge or charge exceeds battery capacity (throw exception? return a value? indicate to caller that something happened!)

- try to move more model-specific variables to basic_battery, as base_battery is supposed to be extensible across all possible batteries.

- avoid magic numbers

- fix pass on update function in BaseBattery, let BasicBattery override it (this is valid, as Python will leave something not implemented in a subclass when you don't declare it again)

##Motor

DC Voltage, DC Current is needed to obtain energy consumed
DC Voltage is given by the Battery
DC Current depends on many factors:
    - Road, Tire Friction = 0.7
    - Vehicle Mass = 250 kg
    - Vehicle Acceleration = 0
    - Vehicle Speed = user determined

    - (Mass * gravity * friction)/(Wheel Radius) = Torque
    - motor_controller_efficiency = f(Torque, speed)
    - motor_output_power = Torque * angular_speed
    - motor_input_power = (Torque * angular_speed)/motor_efficiency 
    - motor_controller_input_power = (Torque * angular_speed)/(mc_efficiency * motor_efficiency)
    - motor_controller_input = (Torque * angular_speed)/(mc_efficiency * motor_efficiency * input voltage)






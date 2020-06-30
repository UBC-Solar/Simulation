import simulation
import numpy as np
import datetime
import time as timer

"""
Description: Given a constant driving speed, find the range at the speed
before the battery runs out [speed -> distance]
"""

# ----- Simulation input -----

speed = float(input("Enter a speed (km/h): "))


simulation_duration = 60 * 60 * 9
tick = 1

class ExampleSimulation:

    def __init__(self, lvs_power_loss, max_speed):
    """
    Instantiates a simple model of the car

    lvs_power_loss: power loss in Watts due to the lvs system
    max_speed: maximum speed of the vehicle on horizontal ground, with no
                wind
    """
        #TODO: replace max_speed with a direct calculation taking into account the 
        #   elevation and wind_speed

        # ----- Simulation constants -----

        #TODO: Replace with the actual model
        self.incident_sunlight = 1000
        self.initial_battery_charge = 0.9

        self.lvs_power_loss = lvs_power_loss
        #self.lvs_power_loss = 0
            
        self.max_speed = max_speed
        #self.max_speed = 104

        # ----- Component initialisation -----
   
        #TODO: convert the array class to use the new model 
        self.basic_array = simulation.BasicArray(incident_sunlight)
        self.basic_array.set_produced_energy(0)
        
        self.basic_battery = simulation.BasicBattery(initial_battery_charge)
        
        self.basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)
         
        self.basic_motor = simulation.BasicMotor()

        #TODO: use the GIS class
        #TODO: use the WeatherForecasts class
        #TODO: use the SolarCalculations class


    def update_model(tick, simulation_duration, initial_battery_charge, speed, \
                    unix_dt, start_coords)
        """
        Updates the model in tick increments for the entire simulation duration. Returns
            a final battery charge and a distance travelled for this duration, given an 
            initial charge, and a target speed. Also requires the current time and location.

        Note: if the speed remains constant throughout this update, and knowing the starting 
            time, the cumulative distance at every time can be known. From the cumulative 
            distance, the GIS class updates the new location of the vehicle. From the location
            of the vehicle at every tick, the gradients at every tick, the weather at every
            tick, the GHI at every tick, is known.
        """

        # ----- Expected Distance Estimate -----

        #TODO: from tick, simulation_duration, speed, create a 1D array of cumulative
        #       distances of size (number of ticks)
        # Also an array of unix_dt with ticks

        #TODO: from cumulative distances array, create a 1D array of "close_enough" indices
        #       of coords from the route of GIS of size (number of ticks)

        #TODO: from "close_enough" GIS indices array, get the elevation at every location
        #       as an 1D array of size (number of ticks)
        # Similarly, get arrays of time differences at every tick and GHI at every tick

        #TODO: from cumulative distances array, create an array of "close_enough" indices 
        #       of coords from the route of Weather
        # Get the weather at every location

        # ----- Energy calculations -----
    
        self.basic_array.update(tick)
         
        self.basic_lvs.update(tick)
        lvs_consumed_energy = basic_lvs.get_consumed_energy()
   
        #TODO: convert the motor class to receive both the speed, and a range of
        #       elevations
        #TODO: calculate new motor_consumed_energy from this 
        self.basic_motor.calculate_power_in(speed)
        self.basic_motor.update(tick)
        motor_consumed_energy = basic_motor.get_consumed_energy()
        
        #TODO: convert the array class to use the new model 
        #TODO: calculate new array output based on the time and location
        self.produced_energy = basic_array.get_produced_energy()
        consumed_energy = motor_consumed_energy + lvs_consumed_energy
         
        # net energy added to the battery
        net_energy = produced_energy - consumed_energy

        #TODO: net_energy should become an array like time
         
        # ----- Array initialisation -----
        
        # array of times for the simulation
        time = np.arange(0, simulation_duration + tick, tick, dtype='f4')
         
        # stores speed of car at each time step
        speed_kmh = np.full_like(time, fill_value=speed, dtype='f4')
         
        # stores the amount of energy transferred from/to the battery at each time step
        #TODO: change the net_energy fill value to be like time
        delta_energy = np.full_like(time, fill_value=net_energy, dtype='f4')

        # used to calculate the time the car was in motion
        tick_array = np.full_like(time, fill_value=tick, dtype='f4')
        tick_array[0] = 0
         
        # ----- Array calculations -----
        cumulative_delta_energy = np.cumsum(delta_energy)
        battery_variables_array = self.basic_battery.update_array(cumulative_delta_energy)
         
        # stores the battery SOC at each time step
        state_of_charge = battery_variables_array[0]
        state_of_charge[np.abs(state_of_charge) < 1e-03] = 0
         
        # when the battery is empty the car will not move
        #TODO: if the car cannot climb the elevation, the car also does not move
        speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh
        time_in_motion = np.logical_and(tick_array, state_of_charge) * tick
         
        time_taken = np.sum(time_in_motion)
        time_taken = str(datetime.timedelta(seconds=int(time_taken)))
         
        final_soc = state_of_charge[-1] * 100 + 0.
    
        # ----- Target value -----
         
        distance = speed * (time_in_motion / 3600)
        distance_travelled = np.sum(distance)

        print(f"\nSimulation successful!\n"
                f"Time taken: {time_taken}\n"
                f"Maximum distance traversable: {distance_travelled:.2f}km\n"
                f"Speed: {speed}km/h\n"
                f"Final battery SOC: {final_soc:.2f}%\n")


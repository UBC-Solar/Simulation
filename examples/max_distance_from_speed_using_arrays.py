import simulation
import numpy as np
from simulation.common import helpers

"""
Description: Given an hourly driving speed, find the range at the speed
before the battery runs out [speed -> distance].
"""


@helpers.timeit
def main():
    # length of the simulation in seconds
    simulation_length = 60 * 60 * 10

    input_speed = np.array([45, 87, 65, 89, 43, 54, 45, 23, 34, 20])

    """
    Note: it no longer matters how many elements the input_speed array has, the simulation automatically
        reshapes the array depending on the simulation_length. 

    Examples:
      If you want a constant speed for the entire simulation, insert a single element
      into the input_speed array. 
      
      >>> input_speed = np.array([30]) <-- constant speed of 30km/h
    
      If you want 50km/h in the first half of the simulation and 60km/h in the second half,
      do the following:

    >>> input_speed = np.array([50, 60])
    
      This logic will apply for all subsequent array lengths (3, 4, 5, etc.)
      
      Keep in mind, however, that the condition len(input_speed) <= simulation_length must be true
    """
    simulation_model = simulation.Simulation("./simulation/main/settings_example.json")

    for _ in range(1):
        distance_travelled = simulation_model.run_model(speed=input_speed, plot_results=True)
        print(distance_travelled)


if __name__ == "__main__":
    main()

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
    simulation_length = 60 * 60 * 12

    input_speed = np.array([35])

    race_type = "FSGP"

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

    google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"
    weather_api_key = "51bb626fa632bcac20ccb67a2809a73b"

    if race_type == "FSGP":
        origin_coord = np.array([38.9267957, -95.67676127])
        # Waypoints obtained from Google Maps 
        waypoints = np.array([38.9272094, -95.6771353], [38.9189985, -95.6752748],
                            [38.9215404, -95.6744271], [38.920318, -95.6709074]
                             [38.9250241,-95.6714015], [38.929093, -95.6774928],
                             [38.929093,-95.6774928], [38.9271993, -95.6771334])

        dest_coord = np.array([38.9243266,-95.6799917])

    elif race_type == "ASC":

        origin_coord = np.array([39.0918, -94.4172])

        waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

        dest_coord = np.array([43.6142, -116.2080])

    simulation_model = simulation.Simulation(google_api_key, weather_api_key, origin_coord, dest_coord, waypoints,
                                                tick=1, simulation_duration=simulation_length, race_type="FSGP")

    for _ in range(1):
        distance_travelled = simulation_model.run_model(speed=input_speed, plot_results=True)
        print(distance_travelled)


if __name__ == "__main__":
    main()

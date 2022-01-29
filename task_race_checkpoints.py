import numpy as np
import itertools as it 
from math import hypot
from haversine import haversine
from matplotlib import pyplot as plt


test_speed_arr = [1, 2, 1, 7, 3, 4] # 6 seconds

test_distance_arr = [] # going to write to this array

example_coord_arr = np.array([[0,1], [0,5], [0,6], [0,8], [0,12]])

result_coord_arr = [] 

#TODO speed_arr_helper
""" 
Convert speed to speed array where each unit is km/s
test_speed_arr won't be given, we need to calculate the speed array given the speed input
the size of the array will also be determined by inputed time parameter
"""

# STEP 1:
def calculate_distance(p1,p2, print=True):
    """Calculate Euclidean distance between two points."""
    x1,y1 = p1
    x2,y2 = p2
    if print:
      print(f"{p1},{p2}") 
    return round(hypot(x2 - x1, y2 - y1), 2)
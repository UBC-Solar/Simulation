import numpy as np
import itertools as it 
from math import hypot
from haversine import haversine
from matplotlib import pyplot as plt

# Most of this code is written by Chris

test_speed_arr = np.array([1, 2, 1, 7, 3, 4]) # 6 seconds

test_distance_arr = [] # going to write to this array

example_path_arr = np.array([[0,1], [0,5], [0,6], [0,8], [0,12]])

result_coord_arr = [] 

#TODO speed_arr_helper
""" 
Convert speed to speed array where each unit is km/s
test_speed_arr won't be given, we need to calculate the speed array given the speed input
the size of the array will also be determined by inputed time parameter
"""

# STEP 1:
# Calculating the distances between two coordinates
def calculate_distance(p1,p2, print=True):
    """Calculate Euclidean distance between two points."""
    x1,y1 = p1
    x2,y2 = p2
    if print:
      print(f"{p1},{p2}") 
    return round(hypot(x2 - x1, y2 - y1), 2)

# STEP 2:
# To calculate the distance between coordinates, first need to convert our path array to pariwise iteration
# Example: String "ABCDEF" -> AB, BC, CD, DE, EF.
# Can show the calculated coordinates
def pairwise(iterable, show=False):
  a, b = it.tee(iterable)
  next(b, None)
  if show:
    for p1, p2 in zip(a, b):
      print(p1, p2)
  return zip(a, b)

def calculate_array_distances(path):
  return np.array([calculate_distance(p1, p2, False) for p1, p2 in pairwise(path)])


test_distance_arr = calculate_array_distances(example_path_arr)

# STEP 3:

# All the contents on this file moved to the notebook file /coord_by_time.ipynb
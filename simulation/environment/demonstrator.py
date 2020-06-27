import numpy as np
import matplotlib.pyplot as plt
import pickle
import pandas as pd

from SolarCalculations import SolarCalculations
from GIS import GIS
from WeatherForecasts import WeatherForecasts

#google api key
google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"

#weather api key
weather_api_key = "51bb626fa632bcac20ccb67a2809a73b" 

#Current Time: 1 June 2020, 07 00
timestamp = 1593586800
timezone = -6

#Starting Point: Independence Square, MO
origin_coord = np.array([39.0918, -94.4172])

#Waypoints: 
# - Brown v Board of Education National Historic Site, Topeka, KS
# - Stuhr Museum of the Prairie Pioneer, Grand Island, NE
# - Scotts Bluff National Monument, Gering, NE
# - National Historic Trails Interpretive Center, Casper, WY
# - Fremont County Pioneer Musem, Lander, WY
# - National Oregon/California Trail Center, Montpelier, ID
# - Herret Center for Art and Science, Twin Falls, ID

waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734], \
            [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452], \
            [42.3224, -111.2973], [42.5840, -114.4703]])

#Ending Point: Jack's Urban Meeting Place, Boise, ID
dest_coord = np.array([43.6142, -116.2080])

"""
#GIS class and get the path variables
gis = GIS(google_api_key, origin_coord, dest_coord, waypoints)
path = gis.get_path()
path_elevations = gis.get_path_elevations()
path_distances = gis.get_path_distances()
path_gradients = gis.get_path_gradients()

#write to pickle file
f = open('path.pickle', 'wb')
pickle.dump((path, path_elevations, path_distances, path_gradients), f, \
            protocol = pickle.HIGHEST_PROTOCOL)
"""

f_2 = open('path.pickle', 'rb')
path,path_elevations,path_distances,path_gradients = pickle.load(f_2)

f_2 = open('weather.pickle', 'rb')
path_weather = pickle.load(f_2)

#Plot elevation against cumulative distance
cumulative_distances = np.cumsum(path_distances)
elevation_fig, elevation_ax = plt.subplots()
elevation_ax.plot(cumulative_distances, path_elevations[1:])
elevation_ax.set_xlabel('cumulative distance in m')
elevation_ax.set_ylabel('path elevations in m')
elevation_ax.set_title("Elevation vs Distance")

#Plot the road gradient against the cumulative distance
df = pd.DataFrame(path_gradients)
rolling = df.rolling(25)
path_gradients = rolling.mean()

gradient_fig, gradient_ax = plt.subplots()
gradient_ax.plot(cumulative_distances, path_gradients)
gradient_ax.set_xlabel('cumulative distance in m')
gradient_ax.set_ylabel('path gradient')
gradient_ax.set_ylabel('path_gradient')
gradient_ax.set_title('Gradient vs Distance')

"""
weather = WeatherForecasts(weather_api_key, path, timestamp)
path_weather = weather.get_path_weather_forecast()

f = open('weather.pickle', 'wb')
pickle.dump(path_weather, f)
"""
#Solar Calculation class
solar = SolarCalculations()

plt.show()

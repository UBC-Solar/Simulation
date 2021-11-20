import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import shapely
import random
import folium

origin_coord = np.array([38.9266274, -95.6781231])

waypoints = np.array([
        [39.0379, -95.6764], [40.8838, -98.3734], [41.8392, -103.7115],
        [42.8663, -106.3372], [42.8408, -108.7452], [42.3224, -111.2973],
        [42.5840, -114.4703]
    ])  # Turn 2, Turn 4, Turn 7, Turn 8, Turn 13

dest_coord = np.array([38.9219577, -95.6776967])

points = []
colours = []
def get_points(x):
    num = len(x) + 1
    i = 1
    while(i < num):
        points.append("Point " + str(i))
        i += 1

def get_colours(y):
    num = len(y) + 1
    i = 1
    while (i < num):
        color = "%06x" % random.randint(0, 0xFFFFFF)
        color = "#" + color
        colours.append(color)
        i += 1

get_points(waypoints)
get_colours(waypoints)
df = pd.DataFrame(waypoints, points, columns=["Lat", "Long"])

geometry = gpd.points_from_xy(df.Long, df.Lat)

#can only plot geo data frames
geo_df = gpd.GeoDataFrame(df[["Lat", "Long"]], geometry=geometry)
part1 = shapely.geometry.LineString(geo_df.geometry)
linegdf = gpd.GeoDataFrame({'geometry': [part1]})

f, ax = plt.subplots(figsize=(10, 5))
ax.set_axis_off()

geo_df.plot(ax=ax, legend=True, color=colours)
linegdf.plot(ax=ax, linewidth=1)
#map = folium.Map(location = [13.406,80.110], tiles='OpenStreetMap' , zoom_start = 9)
start_point = [waypoints[0][1], waypoints[0][0]]
ax.annotate("Start", xy=start_point, xytext=(1,1), textcoords='offset points')
plt.show()

#todo:
#add a folium map
#^^ rescrictions? very limited to what i can do cause folium library
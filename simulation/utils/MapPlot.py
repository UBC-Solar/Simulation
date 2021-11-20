import numpy as np
import os
from simulation.environment import GIS
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
import uuid
import json
import requests
from PIL import Image
from io import BytesIO

BACKGROUND_IMAGE_PATH = './data/images/'
BACKGROUND_COORDINATE_DATA_NAME = 'coordinates.json'
BACKGROUND_COORDINATE_DATA_FULL_NAME = os.path.join(BACKGROUND_IMAGE_PATH, BACKGROUND_COORDINATE_DATA_NAME)

class MapPlot():
  def __init__(self, path, bbox):
    self.path = path
    self.bbox = [bbox[0]-0.5,bbox[1]-0.5,bbox[2]+0.5, bbox[3]+0.5]
    self.json_data = self._loadData()
    self.image_name = self.generateBackground()
    self.background = os.path.join(BACKGROUND_IMAGE_PATH, self.image_name)

  def _findBackground(self) -> str:
    image_coords = self._formatImageCoords()
    if image_coords in self.json_data:
      return self.json_data[image_coords]
    
  def _loadData(self):
    try:
      with open(BACKGROUND_COORDINATE_DATA_FULL_NAME) as file:
        return json.load(file)
    except:
      return {}
    
  def _saveImageCoords(self):
    if self.json_data:
      with open(BACKGROUND_COORDINATE_DATA_FULL_NAME, 'w') as file:
        json.dump(self.json_data, file)

  def _formatImageCoords(self) -> str:
    return f"({self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]})"

  def generateBackground(self) -> str:
    bg = self._findBackground()
    if bg:
      return bg
    load_dotenv()
    key = os.environ.get("MAPBOX_API_KEY")
    r = requests.get(f"https://api.mapbox.com/styles/v1/mapbox/dark-v10/static/[{self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]}]/1200x300?access_token={key}")
    i = Image.open(BytesIO(r.content))
    id = uuid.uuid4()
    name = f"{id}.png"
    i.save(os.path.join(BACKGROUND_IMAGE_PATH, name), format="PNG")
    self.json_data[self._formatImageCoords()] = name
    self._saveImageCoords()
    return name

  def plotPath(self, waypoints):
    bbox = [self.bbox[0], self.bbox[2], self.bbox[1], self.bbox[3]]
    sample = self.path[0::5]
    coords = pd.DataFrame(data=sample, columns=['latitude','longitude'])
    coords_waypoints = pd.DataFrame(data=waypoints, columns=['latitude','longitude'])
    print(coords.head(20))

    bg = plt.imread(self.background)

    fig, ax = plt.subplots(figsize = (8,7))
    ax.plot(coords.longitude, coords.latitude, zorder=1, alpha=0.5, c='r')
    ax.scatter(coords_waypoints.longitude, coords_waypoints.latitude, zorder=2, alpha= 0.5, c='b', s=40)
    ax.set_title('Map')
    ax.set_xlim(bbox[0],bbox[1])
    ax.set_ylim(bbox[2],bbox[3])
    ax.imshow(bg, zorder=0, extent = bbox, aspect= 'equal')
    plt.show()

if __name__ == "__main__":
    google_api_key = ""

    origin_coord = np.array([39.0918, -94.4172])

    waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734], [41.8392, -103.7115],
        [42.8663, -106.3372], [42.8408, -108.7452], [42.3224, -111.2973],
        [42.5840, -114.4703]])  # Turn 2, Turn 4, Turn 7, Turn 8, Turn 13

    dest_coord = np.array([43.6142, -116.2080])

    locationSystem = GIS(api_key=google_api_key, origin_coord=origin_coord, dest_coord=dest_coord, waypoints=waypoints,
                         race_type="ASC", force_update=False)
    map = MapPlot(locationSystem.path, locationSystem.calculate_path_min_max())
    map.plotPath(locationSystem.waypoints)
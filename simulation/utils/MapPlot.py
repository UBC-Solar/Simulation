import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import requests
import uuid
from PIL import Image
from dotenv import load_dotenv
from io import BytesIO
from simulation.environment import GIS

BACKGROUND_IMAGE_PATH = './data/images/'
BACKGROUND_COORDINATE_DATA_NAME = 'coordinates.json'
BACKGROUND_COORDINATE_DATA_FULL_NAME = os.path.join(BACKGROUND_IMAGE_PATH, BACKGROUND_COORDINATE_DATA_NAME)
PADDING = 0.005


class MapPlot():
    def __init__(self, path, bbox):
        self.path = path
        self.bbox = [bbox[0] - PADDING, bbox[1] - PADDING, bbox[2] + PADDING, bbox[3] + PADDING]
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
        r = requests.get(
            f"https://api.mapbox.com/styles/v1/mapbox/dark-v10/static/[{self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]}]/1200x300?access_token={key}")
        i = Image.open(BytesIO(r.content))
        id = uuid.uuid4()
        name = f"{id}.png"
        i.save(os.path.join(BACKGROUND_IMAGE_PATH, name), format="PNG")
        self.json_data[self._formatImageCoords()] = name
        self._saveImageCoords()
        return name

    def plotPath(self, waypoints):
        bbox = [self.bbox[0], self.bbox[2], self.bbox[1], self.bbox[3]]
        # sample = self.path[0::5]
        coords = pd.DataFrame(data=self.path, columns=['latitude', 'longitude'])
        coords_waypoints = pd.DataFrame(data=waypoints, columns=['latitude', 'longitude'])
        print(coords.head(20))
        print(coords_waypoints)

        bg = plt.imread(self.background)

        fig, ax = plt.subplots(figsize=(8, 7))
        ax.plot(coords.longitude, coords.latitude, zorder=1, alpha=0.5, c='r')
        ax.scatter(coords_waypoints.longitude, coords_waypoints.latitude, zorder=2, alpha=0.5, c='b', s=40)
        ax.set_title('Map')
        ax.set_xlim(bbox[0], bbox[1])
        ax.set_ylim(bbox[2], bbox[3])
        ax.imshow(bg, zorder=0, extent=bbox, aspect='equal')
        plt.show()


if __name__ == "__main__":
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    origin_coord = np.array([38.9281815, -95.6770217])
    dest_coord = np.array([38.9282115, -95.6770268])
    waypoints = np.array([
        [38.9221906, -95.6762981],
        [38.9217086, -95.6767896], [38.9189926, -95.6753145], [38.9196768, -95.6724799],
        [38.9196768, -95.6724799], [38.9247448, -95.6714528], [38.9309102, -95.6749362],
        [38.928188, -95.6770129]
    ])

    locationSystem = GIS(api_key=google_api_key, origin_coord=origin_coord, dest_coord=dest_coord, waypoints=waypoints,
                         race_type="FSGP", force_update=True)
    map = MapPlot(locationSystem.path, locationSystem.calculate_path_min_max())
    map.plotPath(locationSystem.waypoints)

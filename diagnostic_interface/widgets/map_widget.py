import numpy as np
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import os
import tempfile
from PyQt5.QtCore import QUrl
from numpy.typing import NDArray
import math


class FoliumMapWidget(QWebEngineView):
    def __init__(self, coords, parent=None):
        super().__init__(parent)
        self.lap_num = 0
        self.model = None
        self.temp_dir = tempfile.gettempdir()
        self.coords = np.array(coords)

    def update_map(self, vertex_values: NDArray[float], units: str = ""):
        assert len(vertex_values) == len(self.coords)

        for i, v in enumerate(vertex_values):
            if math.isnan(v):
                # get neighbors (you may want to special-case ends)
                prev = vertex_values[i - 1] if i > 0 else 0.0
                nxt = vertex_values[i + 1] if i < len(vertex_values) - 1 else prev
                vertex_values[i] = (prev + nxt) / 2.0

        norm = mcolors.Normalize(vmin=min(vertex_values), vmax=max(vertex_values))
        cmap = cm.get_cmap('YlOrRd')

        map_centroid = [np.mean(self.coords[:, 0]), np.mean(self.coords[:, 1])]

        # Create map
        fmap = folium.Map(
            location=map_centroid,
            zoom_start=15.5,
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False,
            doubleClickZoom=False,
            touchZoom=False,
        )
        for i, (coord, vertex_value) in enumerate(zip(self.coords, vertex_values)):
            color = mcolors.to_hex(cmap(norm(vertex_value)))

            current_coord = self.coords[i]
            next_coord = self.coords[i + 1] if i < len(self.coords) - 1 else self.coords[-1]
            # print(f"{color} -> {vertex_value}")

            folium.PolyLine(
                locations=[current_coord, next_coord],
                color=color,
                weight=5,
                tooltip=f"{vertex_value:.1f} {units}",
                popup=f"Segment speed: {vertex_value:.1f} {units}",
            ).add_to(fmap)

        # Save and display
        filepath = os.path.join(self.temp_dir, "optimized_route_map.html")
        fmap.save(filepath)
        self.load(QUrl.fromLocalFile(filepath))

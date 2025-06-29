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


class RealtimeMapWidget(QWebEngineView):
    def __init__(self, zoom=15.5, parent=None):
        super().__init__(parent)
        self.lap_num = 0
        self.model = None
        self.zoom = zoom
        self.temp_dir = tempfile.gettempdir()

    def update_map(self, vertex_values: NDArray[float], latitudes: NDArray, longitudes: NDArray, units: str = "", map_centroid=None):
        assert len(vertex_values) == len(latitudes) == len(longitudes)

        for i, v in enumerate(vertex_values):
            if math.isnan(v):
                # get neighbors (you may want to special-case ends)
                prev = vertex_values[i - 1] if i > 0 else 0.0
                nxt = vertex_values[i + 1] if i < len(vertex_values) - 1 else prev
                vertex_values[i] = (prev + nxt) / 2.0

        norm = mcolors.Normalize(vmin=min(vertex_values), vmax=max(vertex_values))
        cmap = cm.get_cmap('YlOrRd')

        if map_centroid is None:
            map_centroid = [np.mean(latitudes), np.mean(longitudes)]

        # Create map
        fmap = folium.Map(
            location=map_centroid,
            zoom_start=self.zoom,
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False,
            doubleClickZoom=False,
            touchZoom=False,
        )

        get_coord = lambda x: [latitudes[x], longitudes[x]]

        for i, (latitude, longitude, vertex_value) in enumerate(zip(latitudes, longitudes, vertex_values)):
            color = mcolors.to_hex(cmap(norm(vertex_value)))

            current_coord = get_coord(i)
            next_coord = get_coord(i + 1) if i < len(latitudes) - 1 else get_coord(-1)

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

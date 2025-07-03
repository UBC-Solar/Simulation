import folium
from folium.plugins import MeasureControl

import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors

def plot_mesh(heat_map, trajectory, mesh, distances, speeds, energies, times, cornering_work, gradients, road_friction_array, drag_forces, g_forces):
    heat_map_options = {"energy", "speed"}
    if heat_map not in heat_map_options:
        raise ValueError("Invalid heatmap option passed to plot_mesh. Muse be either \"energy\" or \"speed\"")

    if heat_map == "energy":
        plot_value = energies
    else:
        plot_value = speeds

    map_center = trajectory[0]
    m = folium.Map(location=map_center, zoom_start=15)

    m.add_child(MeasureControl()) # adds measurement tool
    # Use percentiles to suppress the influence of outliers
    lower = np.percentile(plot_value, 15)  
    upper = np.percentile(plot_value, 95)

    norm = mcolors.Normalize(vmin=lower, vmax=upper)
    cmap = cm.get_cmap('plasma')

    # Plot the lateral mesh points
    # for i, row in enumerate(mesh):
    #     if len(row) < 2:
    #         continue
    #     for j, (lat, lon) in enumerate(row):
    #         folium.CircleMarker(
    #             location=(lat, lon),
    #             radius=2,
    #             color='red',
    #             fill=True,
    #             fill_opacity=0.7
    #         ).add_to(m)
    #
    #     folium.PolyLine(row, color='gray', weight=1, opacity=0.5).add_to(m)

    # Plot colored line segments between each pair of points
    for i in range(len(trajectory) - 1):
        latlon_start = trajectory[i]
        latlon_end = trajectory[i + 1]

        # Average between the two points
        avg_value = (plot_value[i] + plot_value[i + 1]) / 2
        rgba = cmap(norm(avg_value))
        hex_color = mcolors.to_hex(rgba)

        folium.PolyLine(
            locations=[latlon_start, latlon_end],
            color=hex_color,
            weight=3,
            opacity=0.8
        ).add_to(m)

    incline_angles = np.degrees(np.arctan(gradients))

    speeds_processed = speeds - np.mean(speeds)

    # attach metadata to chosen points
    for i, (lat, lon) in enumerate(trajectory):
        val = plot_value[i]
        rgba = cmap(norm(val))  # RGBA tuple
        hex_color = mcolors.to_hex(rgba)  # Convert to hex for folium
        metadata = (
            f"<b>General Information</b>"
            f"<br>Trajectory Point: {i}"
            f"<br>Distance (m): {distances[i]:.2f}"
            f"<br>Speed (km/h): {speeds_processed[i]:.2f}"
            f"<br>Time (s): {times[i]:.2f}"
            f"<br>Incline Angle (°): {incline_angles[i]:.2f}"
            f"<hr style='margin:5px 0'>"
            f"<b>⚡ Energy Calculations</b> (J)"
            f"<br>Energy Consumed: {energies[i]:.2f}"
            f"<br>Cornering Work: {cornering_work[i]:.2f}"
            f"<hr style='margin:5px 0'>"
            f"<b>🫸🏼 Force Calculations</b> (N)"
            f"<br>Drag Force: {drag_forces[i]:.2f}"
            f"<br>Rolling Resistance: {road_friction_array[i]:.2f}"
            f"<br>Downforce: {g_forces[i]:.2f}"
        )
        folium.CircleMarker(
            location=(lat, lon),
            radius=4,
            color=hex_color,
            fill=True,
            fill_color=hex_color,
            fill_opacity=0.8,
            popup=folium.Popup(metadata, max_width=300),  
            tooltip=f"Speed: {speeds_processed[i]:.2f}"
        ).add_to(m)



    return m
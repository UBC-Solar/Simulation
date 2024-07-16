from collections import OrderedDict

from simulation.cmd.run_simulation import run_simulation, SimulationSettings
from simulation.model.Simulation import Simulation

import argparse
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import mplcursors
import numpy as np
plt.style.use('seaborn-v0_8-dark')


def calculate_coords(lap_num, coords, num_coordinates, gis_indices, speed_kmh):
    beginning_coordinate = num_coordinates * lap_num
    end_coordinate = num_coordinates * (lap_num + 1)
    coords_of_interest = coords[beginning_coordinate:end_coordinate + 1]

    gis_index_mean_speeds = OrderedDict()

    for i in range(len(coords_of_interest)):
        lap_offset = num_coordinates * lap_num
        k = i + lap_offset
        j = k
        while True:
            indices = np.where(gis_indices == k)[0]
            try:
                begin, end = indices[0], indices[-1] + 1
            except IndexError:
                gis_index_mean_speeds[k - lap_offset] = -1
                k += 1
                continue

            for index in range(j, k + 1):
                gis_index_mean_speeds[index - lap_offset] = np.mean(speed_kmh[begin:end])
            break

    return gis_index_mean_speeds, coords_of_interest


def display_speeds(model: Simulation):
    num_coordinates = int(model.gis.num_unique_coords)
    gis_indices, speed_kmh = model.get_results(["closest_gis_indices", "speed_kmh"])
    coords = model.gis.get_path()

    norm = plt.Normalize(0, 80)
    cmap = plt.get_cmap('gist_ncar')
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    fig = plt.figure(figsize=(12, 8))
    lap_num = 0
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 0.033], wspace=0.05)
    ax = fig.add_subplot(gs[0, 0])
    cax = fig.add_subplot(gs[0, 1])

    norm = plt.Normalize(0, 80)
    cmap = plt.get_cmap('gist_ncar')
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, fraction=1.0)
    cbar.ax.tick_params(labelsize=10)
    cbar.set_label('Speeds (km/h)', fontsize=12)

    lap_num = 0

    def on_key(event):
        nonlocal lap_num
        if event.key == 'right':
            lap_num += 1
        elif event.key == 'left':
            lap_num -= 1
        else:
            return

        if lap_num < 0:
            lap_num = 0
        plot_data(lap_num, coords, num_coordinates, gis_indices, speed_kmh, ax, cmap, norm)

    fig.canvas.mpl_connect('key_press_event', on_key)
    plot_data(lap_num, coords, num_coordinates, gis_indices, speed_kmh, ax, cmap, norm)

cursor = None

def plot_data(index, coords, num_coordinates, gis_indices, speed_kmh, ax, cmap, norm):
    gis_index_mean_speeds, relevant_coords = calculate_coords(index, coords, num_coordinates, gis_indices, speed_kmh)

    ax.clear()

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)

    ax.set_title(f"Predicted optimized speeds for lap {index}")

    lines = []
    for j, (start, stop) in enumerate(zip(relevant_coords[:-1], relevant_coords[1:])):
        y, x = zip(start, stop)
        line, = ax.plot(x, y, color=cmap(norm(gis_index_mean_speeds[j])), linewidth=7.0)
        lines.append(line)

    # Create a cursor and attach it to the figure
    global cursor
    if cursor is not None:
        cursor.remove()
    cursor = mplcursors.cursor(lines, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        index = lines.index(sel.artist)
        sel.annotation.set(text=f"Speed: {gis_index_mean_speeds[index]:.1f}", fontsize=11,
                           bbox=dict(facecolor='white', alpha=0.8))

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_type", required=False, default="FSGP", help="Define which race should be simulated. ("
                                                                            "ASC/FSGP)", type=str)
    parser.add_argument("--granularity", required=False, default=1, help="Define how granular the speed array should "
                                                                         "be, where 1 is hourly and 2 is bi-hourly.",
                        type=int)
    parser.add_argument('-s', "--speeds", required=True, help="Name of cached speed array (.npy extension is assumed, do not include)", type=str)

    parser.add_argument('-p', "--plot", required=False, default=False, help="Plot results of Simulation", type=bool)

    args = parser.parse_args()

    model = run_simulation(SimulationSettings(race_type=args.race_type, verbose=False, granularity=args.granularity), speeds_filename=args.speeds, plot_results=args.plot)
    print(args.plot)
    display_speeds(model)

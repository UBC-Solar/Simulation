import json

import numpy as np


def extrude_normal(path, num_offsets=5, offset_dist=0.001, plot_arrows=False):
    """
    Extrude a closed path in the normal direction.

    Parameters:
        path (np.ndarray): An (n, 2) array of points representing a closed path.
        num_offsets (int): Number of offset points on each side (total extrusions = 2*num_offsets).
                           (Note: The original center point is not included.)
        offset_dist (float): Distance between successive extruded points.

    Returns:
        np.ndarray: An (n, 2*num_offsets, 2) array containing the extruded points.
    """
    # Calculate tangent vectors using circular indexing
    rolled_path = np.roll(path, shift=-1, axis=0)
    tangents = rolled_path - path

    # Calculate normal vectors by rotating the tangents by 90 degrees
    # Rotating (dx, dy) by 90 degrees counter-clockwise gives (-dy, dx)
    normals = np.array([[-dy, dx] for dx, dy in tangents])

    # Normalize the normal vectors
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)

    if plot_arrows:
        plt.plot(path[:, 0], path[:, 1], 'b-', label='Path')

        # Plot the normal vectors
        scale = 0.03  # Scale factor for normal vector length
        mean_length = np.mean(np.linalg.norm(tangents, axis=1))
        for point, normal in zip(path, normals):
            plt.arrow(point[0], point[1], scale * normal[0], scale * normal[1],
                      head_width=0.1 * scale, head_length=0.1 * scale, fc='green', ec='green')

        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Closed Path and Normal Vectors')
        plt.legend()
        plt.grid(True)
        plt.axis('equal')
        plt.show()

    # For num_offsets=5, we get offsets:[-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]
    positive_offsets = np.arange(1, num_offsets + 1)
    negative_offsets = np.arange(-num_offsets, 0)

    # Create the extruded points. For each point on the path, add offsets along the normal.
    # Here we use broadcasting to create an (n, 10, 2) array.
    positive_extruded_points = path[None, :, :] + normals[None, :, :] * (positive_offsets[:, None, None] * offset_dist)
    negative_extruded_points = path[None, :, :] + normals[None, :, :] * (negative_offsets[:, None, None] * offset_dist)

    extruded_points = np.concatenate([positive_extruded_points, path[None, :, :], negative_extruded_points], axis=0)

    return extruded_points


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    plot_paths = False
    plot_arrows = True

    with open("/Users/joshuariefman/Simulation/simulation/config/settings_FSGP.json") as json_file:
        path = np.array(json.load(json_file)["waypoints"])

    if plot_paths:
        x = path[:, 0]
        y = path[:, 1]

        plt.scatter(x, y, marker='o', color='b', zorder=5)
        plt.title("Original Path")

        plt.show()

    # Normalize path
    path[:, 0] = path[:, 0] - np.mean(path[:, 0])
    path[:, 1] = path[:, 1] - np.mean(path[:, 1])

    max_element = max(np.max(path[:, 0]), np.max(path[:, 1]))

    path[:, 0] /= max_element
    path[:, 1] /= max_element

    if plot_paths:
        x = path[:, 0]
        y = path[:, 1]

        plt.scatter(x, y, marker='o', color='b', zorder=5)
        plt.title("Normalized Path")

        plt.show()

    # Extrude normal to each point: 5 points on each side (total 10 extruded points per original point)
    extruded = extrude_normal(path, num_offsets=2, offset_dist=0.0075, plot_arrows=plot_arrows)

    for line in extruded:
        plt.plot(line[:, 0], line[:, 1], color='tab:red', zorder=0)

    for i in range(extruded.shape[1]):
        column_sub_manifold = extruded[:, i, :]
        plt.plot(column_sub_manifold[:, 0], column_sub_manifold[:, 1], color='tab:red', zorder=0)

    x = extruded[:, :, 0]
    y = extruded[:, :, 1]

    plt.scatter(x, y, marker='o', color='b', zorder=5, s=10)
    plt.axis('equal')

    plt.show()



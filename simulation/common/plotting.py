from simulation.common.helpers import plot_graph


class Graph:
    """

    Object to contain information to be plotted.

    """

    def __init__(self, arrays_to_plot, plot_titles, graph_name):
        self.arrays_to_plot = arrays_to_plot
        self.plot_titles = plot_titles
        self.graph_name = graph_name


class Plotting:
    """

    This class exists to organize the plotting of graphs.

    """

    def __init__(self):
        self.graph_queue = []

    def plot_graphs(self, timestamps, plotting_portion: tuple[float] = (0.0, 1.0)):
        """

        Plot all graphs in the graph queue.

        :param np.ndarray timestamps: Array of timestamps which serves as the "x-axis" of graphs.
        :param tuple[float] plotting_portion: A tuple containing percentages that denote the beginning and end of the
        portion of the race that we'd like to plot. For example, if you wanted to plot the second half of the race,
        input (0.5, 1.0).

        """
        assert 0.0 <= plotting_portion[0] < plotting_portion[1] <= 1.0, "plotting_portion is out of bounds!"

        # Graph all graphs that have been queued
        for graph in self.graph_queue:
            plot_graph(timestamps=timestamps,
                       arrays_to_plot=graph.arrays_to_plot,
                       array_labels=graph.plot_titles,
                       graph_title=graph.graph_name,
                       plot_portion=plotting_portion)

        # Remove every graph from the queue after they've been graphed.
        self.graph_queue.clear()

    def add_graph_to_queue(self, new_graph):
        """

        Add a new graph to the plotting queue.

        :param Graph new_graph: Graph object to be added in the queue of graphs to be plotted.

        """

        self.graph_queue.append(new_graph)

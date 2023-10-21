import numpy as np

from simulation.common.helpers import plot_graph


class GraphPage:
    """

    A graph page contains a singular or series of graphs that will be plotted on one page.

    """

    def __init__(self, arrays_to_plot, plot_titles, page_name):
        self.arrays_to_plot = arrays_to_plot
        self.plot_titles = plot_titles
        self.page_name = page_name


class Plotting:
    """

    This class exists to organize the plotting of graphs.

    """

    def __init__(self):
        self.graph_queue = []

    def plot_graph_pages(self, timestamps, plot_portion):
        """

        Plot all graph pages in the queue.

        :param np.ndarray timestamps: Array of timestamps which serves as the "x-axis" of graphs.
        :param tuple[float] plot_portion: A tuple containing percentages that denote the beginning and end of the
        portion of the race that we'd like to plot. For example, if you wanted to plot the second half of the race,
        input (0.5, 1.0).

        """

        # Graph all graphs that have been queued
        for graph in self.graph_queue:
            plot_graph(timestamps=timestamps,
                       arrays_to_plot=graph.arrays_to_plot,
                       array_labels=graph.plot_titles,
                       graph_title=graph.page_name,
                       plot_portion=plot_portion)

        # Remove every graph from the queue after they've been graphed.
        self.graph_queue.clear()

    def add_graph_page_to_queue(self, new_graph):
        """

        Add a new graph page to the plotting queue.

        :param GraphPage new_graph: Graph page object to be added in the queue of graphs to be plotted.

        """

        self.graph_queue.append(new_graph)

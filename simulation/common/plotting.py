import numpy as np
from simulation.common.helpers import plot_graph


class Graph:
    def __init__(self, arrays_to_plot, plot_titles, graph_name):
        self.arrays_to_plot = arrays_to_plot
        self.plot_titles = plot_titles
        self.graph_name = graph_name

    def add_to_graphs(self, array_to_add, plot_title):
        self.arrays_to_plot.append(array_to_add)
        self.plot_titles.append(plot_title)


class GraphsManager:
    def __init__(self):
        self.graph_queue = []

    def plot_graphs(self, timestamps):
        for graph in self.graph_queue:
            plot_graph(timestamps=timestamps,
                       arrays_to_plot=graph.arrays_to_plot,
                       array_labels=graph.plot_titles,
                       graph_title=graph.graph_name)

    def add_graph_to_queue(self, new_graph):
        self.graph_queue.append(new_graph)
